import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';

import { warrantApiClient } from '../services/client';
import type { WarrantResponse } from '../types/api';
import { WarrantIdentifierCorrection } from './WarrantIdentifierCorrection';

vi.mock('../services/client', () => ({ warrantApiClient: { correctIdentifiers: vi.fn() } }));
const warrant: WarrantResponse = {
  id: 'warrant',
  workspace_id: 'workspace',
  issuer_id: 'issuer',
  underlying_id: 'stock',
  display_name: 'BNP Deere Call',
  isin: 'DE000PK72H6',
  wkn: null,
  product_family: 'WARRANT',
  lifecycle_status: 'ACTIVE',
  version: 1,
  created_at: '',
  updated_at: '',
};
beforeEach(() => vi.clearAllMocks());

it('corrects the same product with version and evidence, without writing trading data', async () => {
  const updated = { ...warrant, isin: 'DE000VH2LU21', version: 2 };
  vi.mocked(warrantApiClient.correctIdentifiers).mockResolvedValue(updated);
  const onSaved = vi.fn();
  render(<WarrantIdentifierCorrection warrant={warrant} onSaved={onSaved} />);
  fireEvent.click(screen.getByText('Kennungen korrigieren'));
  fireEvent.change(screen.getByLabelText('Verifizierte ISIN'), { target: { value: updated.isin } });
  fireEvent.change(screen.getByLabelText('Beleg / Quelle der Korrektur'), {
    target: { value: 'Testbeleg' },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Kennungen speichern' }));
  await waitFor(() => expect(onSaved).toHaveBeenCalledWith(updated));
  expect(warrantApiClient.correctIdentifiers).toHaveBeenCalledWith('warrant', {
    expected_version: 1,
    isin: updated.isin,
    wkn: null,
    evidence: 'Testbeleg',
  });
  expect(screen.getByRole('status')).toHaveTextContent('erneut geprüft');
});

it('shows a conflicting correction without replacing the selected product', async () => {
  vi.mocked(warrantApiClient.correctIdentifiers).mockRejectedValue(new Error('Version geändert'));
  const onSaved = vi.fn();
  const { container } = render(<WarrantIdentifierCorrection warrant={warrant} onSaved={onSaved} />);
  fireEvent.submit(container.querySelector('form')!);
  expect(await screen.findByText('Version geändert')).toBeInTheDocument();
  expect(onSaved).not.toHaveBeenCalled();
});
