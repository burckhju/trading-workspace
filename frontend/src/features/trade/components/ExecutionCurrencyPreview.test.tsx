import { useState } from 'react';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';

import { tradeManagementApiClient } from '../services/client';
import { emptyExecutionCurrency } from '../services/executionCurrency';
import type { ExecutionCurrencyPreviewContext, ExecutionCurrencyResolution } from '../types/api';
import { ExecutionCurrencyPreview } from './ExecutionCurrencyPreview';

vi.mock('../services/client', () => ({
  tradeManagementApiClient: { executionCurrencyPreview: vi.fn() },
}));
const read = vi.mocked(tradeManagementApiClient.executionCurrencyPreview);
const inherited: ExecutionCurrencyResolution = {
  currency_code: 'EUR',
  source: 'PRIOR_BUYS',
  source_execution_ids: ['synthetic-buy'],
  confirmation_ids: ['synthetic-confirmation'],
};
const unknown: ExecutionCurrencyResolution = {
  currency_code: null,
  source: 'UNKNOWN',
  source_execution_ids: [],
  confirmation_ids: [],
  reason: 'NO_HISTORICAL_EVIDENCE',
};
const historical: ExecutionCurrencyResolution = {
  ...inherited,
  source: 'HISTORICAL_LISTINGS',
  source_execution_ids: [],
  confirmation_ids: [],
  evidence_ids: ['synthetic-source'],
  resolver_version: 'execution-currency-v3',
  evidence: [
    {
      id: 'synthetic-source',
      kind: 'HISTORICAL_LISTINGS',
      source_reference: 'Synthetische Archivquelle',
      recorded_at: '2026-08-01T12:00:00Z',
      valid_from: '2026-08-01T00:00:00Z',
      valid_to: '2026-09-01T00:00:00Z',
    },
  ],
};
function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => {
    resolve = done;
  });
  return { promise, resolve };
}
function Form({
  context = { tradeId: 'trade-a', side: 'SELL' },
  date = '2026-08-20',
  time = '',
}: {
  context?: ExecutionCurrencyPreviewContext;
  date?: string;
  time?: string;
}) {
  const [value, onChange] = useState(emptyExecutionCurrency);
  return (
    <>
      <ExecutionCurrencyPreview
        context={context}
        date={date}
        time={time}
        value={value}
        onChange={onChange}
      />
      <output aria-label="Manuelle Währungsangabe">{JSON.stringify(value)}</output>
    </>
  );
}
beforeEach(() => {
  vi.resetAllMocks();
  read.mockResolvedValue(inherited);
});

it('shows the owner currency for the exact new execution date without creating a declaration', async () => {
  render(<Form />);
  expect(
    await screen.findByText('Vorhandene Währung: EUR · aus vorherigen Käufen übernommen'),
  ).toBeVisible();
  expect(read).toHaveBeenCalledWith(
    { tradeId: 'trade-a', side: 'SELL' },
    {
      executed_on: '2026-08-20',
      execution_timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    },
    expect.any(AbortSignal),
  );
  expect(screen.queryByLabelText('Ausführungswährung (Code)')).not.toBeInTheDocument();
  expect(screen.getByLabelText('Manuelle Währungsangabe')).toHaveTextContent(
    '{"code":"","note":""}',
  );
  expect(screen.getByText('Verwendete Währungsherkunft').closest('details')).not.toHaveAttribute(
    'open',
  );
});

it('omits repeated initial BUY input only after historical evidence arrives and keeps source details available', async () => {
  read.mockResolvedValue(historical);
  render(<Form context={{ productId: 'product-a', side: 'BUY' }} />);
  expect(
    await screen.findByText(/Vorhandene Währung: EUR · automatisch aus historischen/),
  ).toBeVisible();
  expect(screen.queryByLabelText('Ausführungswährung (Code)')).not.toBeInTheDocument();
  expect(read).toHaveBeenCalledWith(
    { productId: 'product-a', side: 'BUY' },
    expect.any(Object),
    expect.any(AbortSignal),
  );
  fireEvent.click(screen.getByText('Verwendete Währungsherkunft'));
  expect(screen.getByText('Quelle: Synthetische Archivquelle')).toBeVisible();
  expect(screen.getByText(/Gültig von 2026-08-01/)).toBeVisible();
  expect(screen.getByLabelText('Manuelle Währungsangabe')).toHaveTextContent(
    '{"code":"","note":""}',
  );
});

it('preserves an explicit manual correction and note when a late historical answer arrives', async () => {
  const pending = deferred<ExecutionCurrencyResolution>();
  read.mockReturnValue(pending.promise);
  render(<Form context={{ productId: 'product-a', side: 'BUY' }} />);
  fireEvent.change(screen.getByLabelText('Ausführungswährung (Code)'), {
    target: { value: 'USD' },
  });
  fireEvent.change(screen.getByLabelText('Beleg / Erläuterung (optional)'), {
    target: { value: 'Meine tatsächliche Abrechnung' },
  });
  await act(async () => {
    pending.resolve(historical);
    await pending.promise;
  });
  expect(screen.getByLabelText('Ausführungswährung (Code)')).toHaveValue('USD');
  expect(screen.getByLabelText('Beleg / Erläuterung (optional)')).toHaveValue(
    'Meine tatsächliche Abrechnung',
  );
  expect(screen.getByText(/erst mit dem Speichern bestätigt und hat Vorrang/)).toBeVisible();
  fireEvent.click(screen.getByRole('button', { name: 'Abweichende Währung verwerfen' }));
  expect(screen.queryByLabelText('Ausführungswährung (Code)')).not.toBeInTheDocument();
});

it.each([
  ['UNKNOWN', 'NO_HISTORICAL_EVIDENCE', 'Für den Ausführungszeitraum fehlt'],
  ['MIXED', 'MULTIPLE_LISTING_CURRENCIES', 'Die historischen Handelsplätze verwenden'],
  ['CONFLICT', 'DOCUMENT_CONFLICT', 'Die zugeordneten Ausführungsbelege nennen'],
] as const)(
  'asks only for unresolved currency when the owner reports %s',
  async (source, reason, message) => {
    read.mockResolvedValue({ ...unknown, source, reason });
    render(<Form />);
    expect(await screen.findByText(new RegExp(message))).toBeVisible();
    expect(screen.getByLabelText('Ausführungswährung (Code)')).toHaveValue('');
    expect(screen.queryByText(/Vorhandene Währung:/)).not.toBeInTheDocument();
    expect(
      screen.getByText(/Ohne Klärung bleibt die Währung unbekannt oder widersprüchlich/),
    ).toBeVisible();
  },
);

it('discards an obsolete date response and never extends a historical source to another day', async () => {
  const old = deferred<ExecutionCurrencyResolution>();
  read.mockReturnValueOnce(old.promise).mockResolvedValueOnce(unknown);
  const view = render(<Form context={{ productId: 'product-a', side: 'BUY' }} />);
  const firstSignal = read.mock.calls[0][2];
  view.rerender(<Form context={{ productId: 'product-a', side: 'BUY' }} date="2026-09-20" />);
  await screen.findByText(/Für den Ausführungszeitraum fehlt/);
  await act(async () => {
    old.resolve(historical);
    await old.promise;
  });
  expect(firstSignal?.aborted).toBe(true);
  expect(screen.queryByText(/Vorhandene Währung:/)).not.toBeInTheDocument();
  expect(screen.getByLabelText('Ausführungswährung (Code)')).toHaveValue('');
});

it('isolates A → B → A reads even when the first A response completes last', async () => {
  const old = deferred<ExecutionCurrencyResolution>();
  read
    .mockReturnValueOnce(old.promise)
    .mockResolvedValueOnce({ ...inherited, currency_code: 'USD' })
    .mockResolvedValueOnce(unknown);
  const view = render(<Form />);
  view.rerender(<Form context={{ tradeId: 'trade-b', side: 'BUY' }} />);
  await screen.findByText(/Vorhandene Währung: USD/);
  view.rerender(<Form />);
  await screen.findByText(/Für den Ausführungszeitraum fehlt/);
  await act(async () => {
    old.resolve(inherited);
    await old.promise;
  });
  expect(screen.queryByText(/Vorhandene Währung:/)).not.toBeInTheDocument();
  expect(read).toHaveBeenCalledTimes(3);
});

it('retains manual input through a failed read and its explicit read-only retry', async () => {
  read
    .mockRejectedValueOnce(new Error('Quelle vorübergehend nicht lesbar'))
    .mockResolvedValueOnce(historical);
  render(<Form context={{ productId: 'product-a', side: 'BUY' }} />);
  await screen.findByText(/Währungsherkunft derzeit nicht geprüft/);
  fireEvent.change(screen.getByLabelText('Ausführungswährung (Code)'), {
    target: { value: 'CHF' },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Währungsherkunft erneut prüfen' }));
  await screen.findByText(/Vorhandene Währung: EUR/);
  expect(screen.getByLabelText('Ausführungswährung (Code)')).toHaveValue('CHF');
  expect(read).toHaveBeenCalledTimes(2);
});

it('does not read an invalid date or manufacture a time, price, quantity or currency', async () => {
  render(<Form date="" />);
  await screen.findByText(/Bitte ein gültiges Kauf-\/Verkaufsdatum/);
  expect(read).not.toHaveBeenCalled();
  expect(screen.getByLabelText('Manuelle Währungsangabe')).toHaveTextContent(
    '{"code":"","note":""}',
  );
});

it('refreshes only the affected trade after an explicit source change and keeps the manual draft', async () => {
  read.mockResolvedValueOnce(inherited).mockResolvedValueOnce(unknown);
  render(<Form />);
  await screen.findByText(/Vorhandene Währung: EUR/);
  fireEvent.click(screen.getByRole('button', { name: 'Abweichende Währung angeben' }));
  fireEvent.change(screen.getByLabelText('Ausführungswährung (Code)'), {
    target: { value: 'CHF' },
  });
  await act(() =>
    window.dispatchEvent(
      new CustomEvent('trade-timeline-changed', { detail: { tradeId: 'trade-b' } }),
    ),
  );
  expect(read).toHaveBeenCalledOnce();
  await act(() =>
    window.dispatchEvent(
      new CustomEvent('trade-timeline-changed', { detail: { tradeId: 'trade-a' } }),
    ),
  );
  await waitFor(() => expect(read).toHaveBeenCalledTimes(2));
  await screen.findByText(/Für den Ausführungszeitraum fehlt/);
  expect(screen.getByLabelText('Ausführungswährung (Code)')).toHaveValue('CHF');
});
