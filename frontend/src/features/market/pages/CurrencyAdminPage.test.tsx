import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';

import {
  currencyAdminClient,
  type CurrencyAdminResponse,
  type CatalogPreview,
} from '../services/currencies';
import { CurrencyAdminPage } from './CurrencyAdminPage';

vi.mock('../services/currencies', () => ({
  currencyAdminClient: {
    list: vi.fn(),
    history: vi.fn(),
    preview: vi.fn(),
    import: vi.fn(),
    changeStatus: vi.fn(),
  },
}));
const api = vi.mocked(currencyAdminClient);
const entry = {
  code: 'GBP',
  name: 'Pound Sterling',
  numeric_code: '826',
  minor_unit: 2,
  kind: 'CURRENCY' as const,
};
const catalog = {
  schema_version: 1 as const,
  version: 'TEST-V1',
  source_url: 'https://www.six-group.com/list-one.xml',
  source_sha256: 'a'.repeat(64),
  source_published_on: '2026-01-01',
  scope: 'Reviewed test subset',
  entries: [entry],
};
const data: CurrencyAdminResponse = {
  catalog,
  catalog_checksum: 'b'.repeat(64),
  items: [
    {
      ...entry,
      catalog_name: entry.name,
      catalog_minor_unit: 2,
      local_exists: false,
      is_active: false,
      catalog_available: true,
      minor_unit_conflict: false,
      can_activate: true,
      reference_version: null,
      state_token: 'c'.repeat(64),
    },
  ],
};
const preview: CatalogPreview = {
  catalog,
  checksum: 'b'.repeat(64),
  current_version: null,
  already_current: false,
  preview_token: 'd'.repeat(64),
  changes: [{ code: 'GBP', change: 'NEW', before: null, after: entry }],
};

beforeEach(() => {
  vi.resetAllMocks();
  api.list.mockResolvedValue(data);
  api.history.mockResolvedValue({ items: [] });
  api.preview.mockResolvedValue(preview);
  api.import.mockResolvedValue({
    applied: true,
    version: catalog.version,
    checksum: preview.checksum,
  });
  api.changeStatus.mockResolvedValue({ code: 'GBP', is_active: true, changed: true });
});

it('requires review before catalog import and never auto-activates currencies', async () => {
  render(<CurrencyAdminPage />);
  await screen.findByRole('button', { name: 'GBP aktivieren' });
  expect(api.import).not.toHaveBeenCalled();
  expect(api.changeStatus).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button', { name: 'Mitgelieferten Katalog prüfen' }));
  const apply = await screen.findByRole('button', { name: 'Katalog übernehmen' });
  expect(apply).toBeDisabled();
  fireEvent.click(screen.getByLabelText(/Ich habe Quelle und Änderungen geprüft/));
  fireEvent.click(apply);
  await screen.findByText(/Katalog übernommen. Keine Währung wurde automatisch aktiviert/);
  expect(api.import).toHaveBeenCalledWith(null, preview.preview_token);
  expect(api.changeStatus).not.toHaveBeenCalled();
});

it('requires separate confirmation and preserves the captured concurrency token', async () => {
  render(<CurrencyAdminPage />);
  fireEvent.click(await screen.findByRole('button', { name: 'GBP aktivieren' }));
  fireEvent.click(screen.getByRole('button', { name: 'Abbrechen' }));
  expect(api.changeStatus).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button', { name: 'GBP aktivieren' }));
  fireEvent.click(screen.getByRole('button', { name: 'Freigabe bestätigen' }));
  await screen.findByText(/GBP wurde aktiviert/);
  expect(api.changeStatus).toHaveBeenCalledWith('GBP', true, data.items[0].state_token);
});

it('supports explicit deactivation and shows history without changing catalog data', async () => {
  api.list.mockResolvedValue({
    ...data,
    items: [{ ...data.items[0], is_active: true, local_exists: true, can_activate: false }],
  });
  api.changeStatus.mockResolvedValue({ code: 'GBP', is_active: false, changed: true });
  api.history.mockResolvedValue({
    items: [
      {
        id: 'audit',
        occurred_at: '2026-09-12T12:00:00Z',
        actor: 'Tester',
        action: 'ACTIVATED',
        aggregate_type: 'CURRENCY',
        changes: {},
      },
    ],
  });
  render(<CurrencyAdminPage />);
  fireEvent.click(await screen.findByRole('button', { name: 'GBP deaktivieren' }));
  fireEvent.click(screen.getByRole('button', { name: 'Freigabe bestätigen' }));
  await screen.findByText(/GBP wurde deaktiviert/);
  expect(api.changeStatus).toHaveBeenCalledWith('GBP', false, data.items[0].state_token);
  expect(screen.getByText(/Tester · ACTIVATED/)).toBeInTheDocument();
});

it('blocks reference conflicts and permits filtering without writes', async () => {
  api.list.mockResolvedValue({
    ...data,
    items: [
      {
        ...data.items[0],
        minor_unit_conflict: true,
        minor_unit: 3,
        can_activate: false,
        local_exists: true,
      },
    ],
  });
  render(<CurrencyAdminPage />);
  expect(await screen.findByRole('button', { name: 'GBP aktivieren' })).toBeDisabled();
  expect(screen.getByText(/Konflikt: Katalog nennt Untereinheit 2/)).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText('Währung suchen'), { target: { value: 'JPY' } });
  expect(screen.getByText('Keine passenden Währungen.')).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText('Währung suchen'), { target: { value: '' } });
  fireEvent.click(screen.getByLabelText('Nur aktive Währungen'));
  expect(screen.getByText('Keine passenden Währungen.')).toBeInTheDocument();
  expect(api.changeStatus).not.toHaveBeenCalled();
});

it('reports failures, supports reload, and discards stale import approval', async () => {
  api.list.mockRejectedValueOnce(new Error('offline'));
  render(<CurrencyAdminPage />);
  expect(await screen.findByRole('alert')).toHaveTextContent('offline');
  fireEvent.click(screen.getByRole('button', { name: 'Stand neu laden' }));
  await screen.findByRole('button', { name: 'GBP aktivieren' });
  api.import.mockRejectedValue(new Error('Bitte eine neue Vorschau erstellen.'));
  fireEvent.click(screen.getByRole('button', { name: 'Mitgelieferten Katalog prüfen' }));
  await screen.findByRole('button', { name: 'Katalog übernehmen' });
  fireEvent.click(screen.getByLabelText(/Ich habe Quelle/));
  fireEvent.click(screen.getByRole('button', { name: 'Katalog übernehmen' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('neue Vorschau');
  expect(screen.queryByRole('button', { name: 'Katalog übernehmen' })).not.toBeInTheDocument();
});

it('previews an uploaded file, rejects oversized files and requires a new review', async () => {
  render(<CurrencyAdminPage />);
  await screen.findByRole('button', { name: 'GBP aktivieren' });
  const input = screen.getByLabelText('Geprüfte Katalogdatei (JSON)');
  const file = new File([JSON.stringify(catalog)], 'reviewed.json');
  Object.defineProperty(file, 'text', { value: () => Promise.resolve(JSON.stringify(catalog)) });
  fireEvent.change(input, { target: { files: [file] } });
  await waitFor(() => expect(screen.getByRole('button', { name: 'Datei prüfen' })).toBeEnabled());
  fireEvent.click(screen.getByRole('button', { name: 'Datei prüfen' }));
  await screen.findByRole('button', { name: 'Katalog übernehmen' });
  expect(api.preview).toHaveBeenCalledWith(JSON.stringify(catalog));
  fireEvent.click(screen.getByLabelText(/Ich habe Quelle/));
  fireEvent.change(input, {
    target: { files: [new File([' '.repeat(256001)], 'too-large.json')] },
  });
  expect(await screen.findByRole('alert')).toHaveTextContent('zu groß');
  expect(screen.queryByRole('button', { name: 'Katalog übernehmen' })).not.toBeInTheDocument();
  expect(api.import).not.toHaveBeenCalled();
});

it('shows absent and already-current catalogs and handles preview/status errors', async () => {
  api.list.mockResolvedValue({ ...data, catalog: null });
  api.preview.mockRejectedValueOnce(new Error('Ungültiger Katalog'));
  render(<CurrencyAdminPage />);
  await screen.findByRole('button', { name: 'GBP aktivieren' });
  expect(screen.getByText(/Noch kein Katalog übernommen/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Mitgelieferten Katalog prüfen' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Ungültiger Katalog');
  api.preview.mockResolvedValue({ ...preview, already_current: true });
  fireEvent.click(screen.getByRole('button', { name: 'Mitgelieferten Katalog prüfen' }));
  await screen.findByText('Dieser Katalog ist bereits übernommen.');
  expect(screen.queryByRole('button', { name: 'Katalog übernehmen' })).not.toBeInTheDocument();
  api.changeStatus.mockRejectedValue(new Error('Bitte neu laden.'));
  fireEvent.click(screen.getByRole('button', { name: 'GBP aktivieren' }));
  const confirmation = screen.getByRole('region', { name: 'Währungsfreigabe bestätigen' });
  fireEvent.click(within(confirmation).getByRole('button', { name: 'Freigabe bestätigen' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Bitte neu laden');
});
