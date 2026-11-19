import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MarketApiError } from '../../market/services/http';
import { readDeadlineExitListing, saveDeadlineExitListing } from '../services/deadlineExitListing';
import { deadlineExitReport, savedDeadlineExitReport } from '../test/deadlineExitListingFixture';
import type { DeadlineExitListingReport } from '../types/deadlineExitListing';
import { DeadlineExitListingChoice } from './DeadlineExitListingChoice';

vi.mock('../services/deadlineExitListing', () => ({
  readDeadlineExitListing: vi.fn(),
  saveDeadlineExitListing: vi.fn(),
}));

beforeEach(() => {
  vi.mocked(readDeadlineExitListing).mockReset().mockResolvedValue(deadlineExitReport());
  vi.mocked(saveDeadlineExitListing).mockReset().mockResolvedValue(savedDeadlineExitReport());
});

const show = () => render(<DeadlineExitListingChoice warrantId="synthetic-warrant" />);
const select = () =>
  screen.getByRole('combobox', { name: 'Vorhandene Notierung für Produkttermine' });
const saveButton = () => screen.getByRole('button', { name: 'Ausstiegshandelsplatz speichern' });

it('never chooses the only listing automatically and keeps passive navigation free of writes', async () => {
  show();
  expect(
    await screen.findByText('Noch kein Ausstiegshandelsplatz ausdrücklich festgelegt.'),
  ).toBeInTheDocument();
  expect(select()).toHaveValue('');
  expect(
    screen.getByRole('option', { name: 'Synthetischer Handelsplatz · XSYN · EUR · SYNTHETIC' }),
  ).toBeInTheDocument();
  expect(saveButton()).toBeDisabled();
  expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
  expect(screen.queryByText('synthetic-listing')).not.toBeInTheDocument();
  expect(screen.queryByText('synthetic-terms')).not.toBeInTheDocument();
  expect(readDeadlineExitListing).toHaveBeenCalledExactlyOnceWith(
    'synthetic-warrant',
    expect.any(AbortSignal),
  );
  expect(saveDeadlineExitListing).not.toHaveBeenCalled();
});

it('saves one explicit business choice and retains it without daily confirmation', async () => {
  const user = userEvent.setup();
  const report = deadlineExitReport();
  show();
  await screen.findByRole('combobox');
  await user.selectOptions(select(), 'synthetic-listing');
  expect(screen.getByText('Auswahl noch nicht gespeichert.')).toBeInTheDocument();
  await user.click(saveButton());
  expect(await screen.findByRole('status')).toHaveTextContent(
    'Diese Wahl bleibt für weitere Prüfdurchläufe erhalten',
  );
  expect(screen.getByText('Gespeicherter Ausstiegshandelsplatz: XSYN')).toBeInTheDocument();
  expect(select()).toHaveValue('synthetic-listing');
  expect(saveButton()).toBeDisabled();
  expect(saveDeadlineExitListing).toHaveBeenCalledExactlyOnceWith(
    'synthetic-warrant',
    report,
    'synthetic-listing',
  );
  expect(readDeadlineExitListing).toHaveBeenCalledOnce();
});

it('reuses a recorded choice and performs no write merely to open its form', async () => {
  vi.mocked(readDeadlineExitListing).mockResolvedValue(savedDeadlineExitReport());
  show();
  expect(await screen.findByText('Gespeicherter Ausstiegshandelsplatz: XSYN')).toBeInTheDocument();
  expect(select()).toHaveValue('synthetic-listing');
  expect(saveButton()).toBeDisabled();
  expect(saveDeadlineExitListing).not.toHaveBeenCalled();
});

it('allows an explicit withdrawal and leaves the previous listing unselected', async () => {
  const user = userEvent.setup();
  const saved = savedDeadlineExitReport();
  vi.mocked(readDeadlineExitListing).mockResolvedValue(saved);
  vi.mocked(saveDeadlineExitListing).mockResolvedValue(
    deadlineExitReport({ revision_number: 2, reasons: ['PRODUCT_EXIT_LISTING_WITHDRAWN'] }),
  );
  show();
  await user.click(await screen.findByRole('button', { name: 'Festlegung zurücknehmen' }));
  expect(await screen.findByRole('status')).toHaveTextContent('Festlegung zurückgenommen');
  expect(select()).toHaveValue('');
  expect(saveButton()).toBeDisabled();
  expect(saveDeadlineExitListing).toHaveBeenCalledExactlyOnceWith('synthetic-warrant', saved, null);
});

it('blocks a stale choice after a 409 and waits for an explicit reread before another write', async () => {
  const user = userEvent.setup();
  vi.mocked(saveDeadlineExitListing).mockRejectedValue(
    new MarketApiError(409, {
      code: 'PRODUCT_EXIT_TERMS_CHANGED',
      message: 'Synthetic changed terms',
      details: [],
      timestamp: '2026-11-18T15:30:00Z',
    }),
  );
  show();
  await screen.findByRole('combobox');
  await user.selectOptions(select(), 'synthetic-listing');
  await user.click(saveButton());
  expect(await screen.findByRole('alert')).toHaveTextContent('zwischenzeitlich geändert');
  expect(select()).toBeDisabled();
  expect(saveButton()).toBeDisabled();
  expect(readDeadlineExitListing).toHaveBeenCalledOnce();
  vi.mocked(readDeadlineExitListing).mockResolvedValue(
    deadlineExitReport({ revision_number: 2, terms_id: 'synthetic-new-terms' }),
  );
  await user.click(screen.getByRole('button', { name: 'Auswahl verwerfen und Stand neu lesen' }));
  expect(select()).toHaveValue('');
  expect(saveButton()).toBeDisabled();
  expect(saveDeadlineExitListing).toHaveBeenCalledOnce();
  expect(readDeadlineExitListing).toHaveBeenCalledTimes(2);
});

it('does not retry an ambiguous write and preserves uncertainty when rereading also fails', async () => {
  const user = userEvent.setup();
  vi.mocked(saveDeadlineExitListing).mockRejectedValue(new Error('synthetic transport failure'));
  show();
  await screen.findByRole('combobox');
  await user.selectOptions(select(), 'synthetic-listing');
  await user.click(saveButton());
  expect(await screen.findByRole('alert')).toHaveTextContent('Speichererfolg unklar');
  vi.mocked(readDeadlineExitListing).mockRejectedValue(new Error('Synthetischer Lesefehler.'));
  await user.click(screen.getByRole('button', { name: 'Auswahl verwerfen und Stand neu lesen' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Synthetischer Lesefehler.');
  expect(screen.getByText(/Der Speichererfolg bleibt ungeklärt/)).toBeInTheDocument();
  expect(select()).toHaveValue('synthetic-listing');
  expect(saveButton()).toBeDisabled();
  expect(saveDeadlineExitListing).toHaveBeenCalledOnce();
});

function deferred() {
  let resolve!: (value: DeadlineExitListingReport) => void;
  const promise = new Promise<DeadlineExitListingReport>((yes) => {
    resolve = yes;
  });
  return { promise, resolve };
}

it('prevents duplicate submission while the first explicit command is pending', async () => {
  const user = userEvent.setup();
  const pending = deferred();
  vi.mocked(saveDeadlineExitListing).mockReturnValue(pending.promise);
  show();
  await screen.findByRole('combobox');
  await user.selectOptions(select(), 'synthetic-listing');
  await user.dblClick(saveButton());
  expect(screen.getByRole('button', { name: 'Festlegung wird gespeichert …' })).toBeDisabled();
  expect(select()).toBeDisabled();
  expect(saveDeadlineExitListing).toHaveBeenCalledOnce();
  await act(async () => {
    pending.resolve(savedDeadlineExitReport());
    await pending.promise;
  });
  expect(screen.getByRole('status')).toHaveTextContent('Ausstiegshandelsplatz gespeichert');
});

it('rejects obsolete A to B to A reads and aborts when the product leaves the view', async () => {
  const first = deferred(),
    second = deferred(),
    third = deferred();
  vi.mocked(readDeadlineExitListing)
    .mockReturnValueOnce(first.promise)
    .mockReturnValueOnce(second.promise)
    .mockReturnValueOnce(third.promise);
  const view = render(<DeadlineExitListingChoice warrantId="synthetic-A" />);
  const firstSignal = vi.mocked(readDeadlineExitListing).mock.calls[0][1];
  view.rerender(<DeadlineExitListingChoice warrantId="synthetic-B" />);
  expect(firstSignal?.aborted).toBe(true);
  view.rerender(<DeadlineExitListingChoice warrantId="synthetic-A" />);
  await act(async () => {
    third.resolve(deadlineExitReport());
    await third.promise;
  });
  await act(async () => {
    first.resolve(savedDeadlineExitReport());
    second.resolve(savedDeadlineExitReport());
    await Promise.all([first.promise, second.promise]);
  });
  expect(select()).toHaveValue('');
  expect(screen.queryByText('Gespeicherter Ausstiegshandelsplatz: XSYN')).not.toBeInTheDocument();
  const lastSignal = vi.mocked(readDeadlineExitListing).mock.calls[2][1];
  view.unmount();
  expect(lastSignal?.aborted).toBe(true);
  expect(saveDeadlineExitListing).not.toHaveBeenCalled();
});
