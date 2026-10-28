import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';

import { currencyConfirmation } from '../../../test/realizedGrossFixtures';
import { MarketApiError } from '../../market/services/http';
import { tradeManagementApiClient } from '../services/client';
import type {
  ExecutionCurrencyConfirmation,
  ExecutionCurrencyHistory,
  ExecutionCurrencyResolution,
} from '../types/api';
import { ExecutionCurrencyPanel } from './ExecutionCurrencyPanel';

vi.mock('../services/client', () => ({
  tradeManagementApiClient: {
    executionCurrencyHistory: vi.fn(),
    confirmExecutionCurrency: vi.fn(),
  },
}));
const api = vi.mocked(tradeManagementApiClient);
function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((yes) => {
    resolve = yes;
  });
  return { promise, resolve };
}
async function open() {
  fireEvent.click(screen.getByRole('button', { name: 'Währung prüfen / bestätigen' }));
  await screen.findByRole('form', { name: 'Ausführungswährung bestätigen' });
}
function affirm(code = 'EUR') {
  fireEvent.change(screen.getByLabelText('Ausführungswährung (Code)'), { target: { value: code } });
}
beforeEach(() => {
  vi.resetAllMocks();
  sessionStorage.clear();
  api.executionCurrencyHistory.mockResolvedValue({ current: null, history: [] });
  api.confirmExecutionCurrency.mockResolvedValue(currencyConfirmation('buy'));
});

it('reads on demand and saves only an explicit confirmation for the exact execution, with one request on double submit', async () => {
  const pending = deferred<ExecutionCurrencyConfirmation>();
  const receipt = currencyConfirmation('buy');
  api.executionCurrencyHistory
    .mockResolvedValueOnce({ current: null, history: [] })
    .mockResolvedValue({ current: receipt, history: [receipt] });
  api.confirmExecutionCurrency.mockReturnValue(pending.promise);
  render(<ExecutionCurrencyPanel tradeId="trade" executionId="buy" />);
  expect(api.executionCurrencyHistory).not.toHaveBeenCalled();
  expect(api.confirmExecutionCurrency).not.toHaveBeenCalled();
  await open();
  expect(screen.getByRole('button', { name: 'Währungsbestätigung speichern' })).toBeDisabled();
  expect(api.executionCurrencyHistory).toHaveBeenCalledWith(
    'trade',
    'buy',
    expect.any(AbortSignal),
  );
  affirm();
  const form = screen.getByRole('form', { name: 'Ausführungswährung bestätigen' });
  fireEvent.submit(form);
  fireEvent.submit(form);
  expect(api.confirmExecutionCurrency).toHaveBeenCalledExactlyOnceWith('trade', 'buy', {
    currency_code: 'EUR',
    source: 'USER_CONFIRMED',
    note: null,
    supersedes_confirmation_id: null,
    request_id: expect.any(String),
  });
  await act(async () => {
    pending.resolve(currencyConfirmation('buy'));
    await pending.promise;
  });
  expect(screen.getByText(/Währung bestätigt. Eine erneute Auswertung/)).toBeVisible();
  expect(screen.getByLabelText('Ausführungswährung (Code)')).toHaveValue('');
  expect(screen.getByText('EUR · ausdrücklich bestätigt')).toBeVisible();
  expect(api.executionCurrencyHistory).toHaveBeenCalledTimes(2);
});

it('pins the read current confirmation, preserves a lost-response retry key and requires a newly entered replacement code', async () => {
  const current = currencyConfirmation('buy');
  api.executionCurrencyHistory.mockResolvedValue({ current, history: [current] });
  api.confirmExecutionCurrency.mockRejectedValue(new Error('Antwort verloren'));
  render(<ExecutionCurrencyPanel tradeId="trade" executionId="buy" confirmation={current} />);
  await open();
  expect(screen.getByLabelText('Ausführungswährung (Code)')).toHaveValue('');
  expect(screen.getByLabelText('Ausführungswährung (Code)')).toHaveValue('');
  affirm('USD');
  fireEvent.click(screen.getByRole('button', { name: 'Währungsbestätigung ersetzen' }));
  await screen.findByRole('alert');
  const first = api.confirmExecutionCurrency.mock.calls[0];
  expect(first[2]).toMatchObject({ currency_code: 'USD', supersedes_confirmation_id: current.id });
  fireEvent.click(screen.getByRole('button', { name: 'Währungsbestätigung ersetzen' }));
  await waitFor(() => expect(api.confirmExecutionCurrency).toHaveBeenCalledTimes(2));
  expect(api.confirmExecutionCurrency.mock.calls[1]).toEqual(first);
  expect(api.executionCurrencyHistory).toHaveBeenCalledOnce();
});

it('requires a deliberate reload and a new explicit save after a concurrent confirmation instead of silently changing the pinned source', async () => {
  const current = currencyConfirmation('buy');
  api.executionCurrencyHistory.mockResolvedValue({ current, history: [current] });
  api.confirmExecutionCurrency.mockRejectedValue(
    new MarketApiError(409, {
      code: 'EXECUTION_CURRENCY_CONFLICT',
      message: 'concurrent',
      details: [],
      timestamp: '2026-10-17T11:00:00Z',
    }),
  );
  render(<ExecutionCurrencyPanel tradeId="trade" executionId="buy" />);
  await open();
  affirm('USD');
  fireEvent.click(screen.getByRole('button', { name: 'Währungsbestätigung ersetzen' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Herkunft neu laden');
  expect(screen.getByRole('button', { name: 'Währungsbestätigung ersetzen' })).toBeDisabled();
  expect(api.executionCurrencyHistory).toHaveBeenCalledOnce();
  const next = {
    ...current,
    id: 'new-current',
    currency_code: 'CHF',
    supersedes_confirmation_id: current.id,
  };
  api.executionCurrencyHistory.mockResolvedValue({ current: next, history: [current, next] });
  fireEvent.click(screen.getByRole('button', { name: 'Währungsherkunft neu laden' }));
  await screen.findByText(/Gelesene Bestätigung: CHF/);
  expect(screen.getByLabelText('Ausführungswährung (Code)')).toHaveValue('');
  expect(api.confirmExecutionCurrency).toHaveBeenCalledOnce();
  affirm('USD');
  fireEvent.click(screen.getByRole('button', { name: 'Währungsbestätigung ersetzen' }));
  await waitFor(() => expect(api.confirmExecutionCurrency).toHaveBeenCalledTimes(2));
  expect(api.confirmExecutionCurrency.mock.calls[1][2].supersedes_confirmation_id).toBe(
    'new-current',
  );
  expect(api.confirmExecutionCurrency.mock.calls[1][2].request_id).not.toBe(
    api.confirmExecutionCurrency.mock.calls[0][2].request_id,
  );
});

it('ignores late reads when the selected trade or execution changes and resets form identity immediately', async () => {
  const old = deferred<ExecutionCurrencyHistory>();
  api.executionCurrencyHistory.mockReturnValueOnce(old.promise);
  const { rerender } = render(<ExecutionCurrencyPanel tradeId="old-trade" executionId="old-buy" />);
  fireEvent.click(screen.getByRole('button', { name: 'Währung prüfen / bestätigen' }));
  const oldSignal = api.executionCurrencyHistory.mock.calls[0][2];
  rerender(<ExecutionCurrencyPanel tradeId="new-trade" executionId="new-buy" />);
  expect(oldSignal?.aborted).toBe(true);
  expect(screen.queryByRole('form')).not.toBeInTheDocument();
  await open();
  affirm('USD');
  await act(async () => {
    old.resolve({
      current: currencyConfirmation('old-buy'),
      history: [currencyConfirmation('old-buy')],
    });
    await old.promise;
  });
  expect(screen.getByLabelText('Ausführungswährung (Code)')).toHaveValue('USD');
  expect(screen.queryByText(/Gelesene Bestätigung: EUR/)).not.toBeInTheDocument();
  api.confirmExecutionCurrency.mockResolvedValue({
    ...currencyConfirmation('new-buy'),
    currency_code: 'USD',
  });
  fireEvent.click(screen.getByRole('button', { name: 'Währungsbestätigung speichern' }));
  await waitFor(() =>
    expect(api.confirmExecutionCurrency).toHaveBeenCalledWith(
      'new-trade',
      'new-buy',
      expect.objectContaining({ currency_code: 'USD' }),
    ),
  );
});

it('does not report a late write as success for a new execution and keeps cancelled history read-only', async () => {
  const pending = deferred<ExecutionCurrencyConfirmation>();
  api.confirmExecutionCurrency.mockReturnValueOnce(pending.promise);
  const { rerender } = render(<ExecutionCurrencyPanel tradeId="trade" executionId="buy" />);
  await open();
  affirm();
  fireEvent.click(screen.getByRole('button', { name: 'Währungsbestätigung speichern' }));
  rerender(<ExecutionCurrencyPanel tradeId="cancelled" executionId="cancelled-buy" readOnly />);
  await act(async () => {
    pending.resolve(currencyConfirmation('buy'));
    await pending.promise;
  });
  expect(screen.queryByText(/Währung bestätigt. Eine erneute/)).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Währungsherkunft ansehen' }));
  await screen.findByText('Keine Bestätigungen gespeichert.');
  expect(screen.queryByRole('form')).not.toBeInTheDocument();
  expect(api.confirmExecutionCurrency).toHaveBeenCalledOnce();
});

it('rejects a read for another execution and recovers after an explicit reload', async () => {
  api.executionCurrencyHistory.mockResolvedValueOnce({
    current: currencyConfirmation('other'),
    history: [],
  });
  render(<ExecutionCurrencyPanel tradeId="trade" executionId="buy" />);
  fireEvent.click(screen.getByRole('button', { name: 'Währung prüfen / bestätigen' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('gehört nicht zu dieser Buchung');
  expect(screen.queryByRole('form')).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Währungsherkunft neu laden' }));
  await screen.findByRole('form', { name: 'Ausführungswährung bestätigen' });
  expect(api.confirmExecutionCurrency).not.toHaveBeenCalled();
});

it('uses the history GET current after a lost-response retry returns an already superseded receipt', async () => {
  const receipt = currencyConfirmation('buy');
  const replacement = {
    ...receipt,
    id: 'replacement-confirmation',
    currency_code: 'USD',
    supersedes_confirmation_id: receipt.id,
  };
  const refreshed = deferred<ExecutionCurrencyHistory>();
  api.confirmExecutionCurrency
    .mockRejectedValueOnce(new Error('Antwort verloren'))
    .mockResolvedValueOnce(receipt);
  api.executionCurrencyHistory
    .mockResolvedValueOnce({ current: null, history: [] })
    .mockReturnValueOnce(refreshed.promise);
  render(<ExecutionCurrencyPanel tradeId="trade" executionId="buy" />);
  await open();
  affirm();
  fireEvent.click(screen.getByRole('button', { name: 'Währungsbestätigung speichern' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Antwort verloren');
  const first = api.confirmExecutionCurrency.mock.calls[0];
  fireEvent.click(screen.getByRole('button', { name: 'Währungsbestätigung speichern' }));
  await waitFor(() => expect(api.executionCurrencyHistory).toHaveBeenCalledTimes(2));
  expect(api.confirmExecutionCurrency.mock.calls[1]).toEqual(first);
  expect(screen.queryByText('EUR · ausdrücklich bestätigt')).not.toBeInTheDocument();
  expect(screen.getByText('Bestätigungsstand wird gelesen…')).toBeVisible();
  expect(screen.queryByRole('form')).not.toBeInTheDocument();
  await act(async () => {
    refreshed.resolve({ current: replacement, history: [receipt, replacement] });
    await refreshed.promise;
  });
  expect(screen.getByText('USD · ausdrücklich bestätigt')).toBeVisible();
  expect(screen.getByText(/Inzwischen gilt ein anderer Bestätigungsstand/)).toBeVisible();
  expect(screen.queryByText('EUR · ausdrücklich bestätigt')).not.toBeInTheDocument();
  expect(screen.getByLabelText('Ausführungswährung (Code)')).toHaveValue('');
  fireEvent.click(screen.getByText('Bisherige Bestätigungen (2)'));
  expect(
    screen.getByText('EUR · historisch ersetzt · ausdrücklich vom Nutzer bestätigt'),
  ).toBeVisible();
  expect(screen.getByText('USD · aktuell · ausdrücklich vom Nutzer bestätigt')).toBeVisible();
});

it('keeps a saved receipt and stale timeline confirmation out of the current display when the refresh fails, then recovers through reading only', async () => {
  const prior = currencyConfirmation('buy');
  const receipt = {
    ...prior,
    id: 'usd-confirmation',
    currency_code: 'USD',
    supersedes_confirmation_id: prior.id,
  };
  api.executionCurrencyHistory
    .mockResolvedValueOnce({ current: prior, history: [prior] })
    .mockRejectedValueOnce(new Error('Lesen nicht verfügbar'))
    .mockResolvedValueOnce({ current: receipt, history: [prior, receipt] });
  api.confirmExecutionCurrency.mockResolvedValue(receipt);
  render(<ExecutionCurrencyPanel tradeId="trade" executionId="buy" confirmation={prior} />);
  await open();
  affirm('USD');
  fireEvent.click(screen.getByRole('button', { name: 'Währungsbestätigung ersetzen' }));
  expect(await screen.findByRole('alert')).toHaveTextContent(
    'Speicherung bestätigt, aktueller Bestätigungsstand aber nicht verfügbar',
  );
  expect(screen.getByText('Aktueller Bestätigungsstand nicht verfügbar')).toBeVisible();
  expect(screen.queryByText('EUR · ausdrücklich bestätigt')).not.toBeInTheDocument();
  expect(screen.queryByText('USD · ausdrücklich bestätigt')).not.toBeInTheDocument();
  expect(screen.queryByRole('form')).not.toBeInTheDocument();
  expect(api.confirmExecutionCurrency).toHaveBeenCalledOnce();
  fireEvent.click(screen.getByRole('button', { name: 'Währungsherkunft neu laden' }));
  expect(await screen.findByText('USD · ausdrücklich bestätigt')).toBeVisible();
  expect(screen.getByLabelText('Ausführungswährung (Code)')).toHaveValue('');
  expect(api.confirmExecutionCurrency).toHaveBeenCalledOnce();
  expect(api.executionCurrencyHistory).toHaveBeenCalledTimes(3);
});

it('does not apply a late post-save history refresh to another trade or execution', async () => {
  const refreshed = deferred<ExecutionCurrencyHistory>();
  const next = { ...currencyConfirmation('new-buy'), currency_code: 'USD' };
  api.executionCurrencyHistory
    .mockResolvedValueOnce({ current: null, history: [] })
    .mockReturnValueOnce(refreshed.promise)
    .mockResolvedValueOnce({ current: next, history: [next] });
  const { rerender } = render(<ExecutionCurrencyPanel tradeId="trade" executionId="buy" />);
  await open();
  affirm();
  fireEvent.click(screen.getByRole('button', { name: 'Währungsbestätigung speichern' }));
  await waitFor(() => expect(api.executionCurrencyHistory).toHaveBeenCalledTimes(2));
  const refreshSignal = api.executionCurrencyHistory.mock.calls[1][2];
  rerender(<ExecutionCurrencyPanel tradeId="new-trade" executionId="new-buy" />);
  expect(refreshSignal?.aborted).toBe(true);
  await open();
  expect(screen.getByText('USD · ausdrücklich bestätigt')).toBeVisible();
  await act(async () => {
    refreshed.resolve({
      current: currencyConfirmation('buy'),
      history: [currencyConfirmation('buy')],
    });
    await refreshed.promise;
  });
  expect(screen.getByText('USD · ausdrücklich bestätigt')).toBeVisible();
  expect(screen.queryByText('EUR · ausdrücklich bestätigt')).not.toBeInTheDocument();
  expect(screen.queryByText(/Währung bestätigt. Eine erneute Auswertung/)).not.toBeInTheDocument();
  expect(api.confirmExecutionCurrency).toHaveBeenCalledOnce();
});

it.each([
  ['PRIOR_BUYS', 'EUR · aus vorherigen Käufen übernommen'],
  ['REPLACED_EXECUTION', 'EUR · aus der ursprünglichen Buchung übernommen'],
  ['EXECUTION_DOCUMENT', 'EUR · automatisch aus Ausführungsbeleg abgeleitet'],
  ['HISTORICAL_LISTING', 'EUR · automatisch aus historischer Notierung abgeleitet'],
  ['HISTORICAL_LISTINGS', 'EUR · automatisch aus historischen Notierungen abgeleitet'],
] as const)(
  'shows %s owner provenance without asking for another confirmation and keeps an override explicit',
  async (source, label) => {
    const resolution: ExecutionCurrencyResolution = {
      currency_code: 'EUR',
      source,
      source_execution_ids: ['original-buy'],
      confirmation_ids: ['buy-evidence'],
    };
    const override = { ...currencyConfirmation('sell'), currency_code: 'USD' };
    api.executionCurrencyHistory
      .mockResolvedValueOnce({ current: null, history: [], currency_resolution: resolution })
      .mockResolvedValue({
        current: override,
        history: [override],
        currency_resolution: {
          currency_code: 'USD',
          source: 'USER_CONFIRMED',
          source_execution_ids: ['sell'],
          confirmation_ids: [override.id],
        },
      });
    api.confirmExecutionCurrency.mockResolvedValue(override);
    render(<ExecutionCurrencyPanel tradeId="trade" executionId="sell" resolution={resolution} />);
    expect(screen.getByText(label)).toBeVisible();
    expect(
      screen.queryByRole('button', { name: 'Währung prüfen / bestätigen' }),
    ).not.toBeInTheDocument();
    expect(api.confirmExecutionCurrency).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: 'Währungsherkunft ansehen' }));
    await screen.findByText(/keine zusätzliche Bestätigung nötig/);
    expect(screen.queryByRole('form')).not.toBeInTheDocument();
    fireEvent.click(screen.getByText('Verwendete Währungsherkunft'));
    expect(screen.getByText('Buchung original-buy')).toBeVisible();
    expect(screen.getByText('Bestätigung buy-evidence')).toBeVisible();
    expect(api.confirmExecutionCurrency).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: 'Abweichende Währung angeben' }));
    affirm('USD');
    expect(screen.queryByRole('checkbox')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Währungsbestätigung speichern' }));
    await screen.findByText('USD · ausdrücklich bestätigt');
    expect(api.confirmExecutionCurrency).toHaveBeenCalledExactlyOnceWith('trade', 'sell', {
      currency_code: 'USD',
      source: 'USER_CONFIRMED',
      note: null,
      supersedes_confirmation_id: null,
      request_id: expect.any(String),
    });
    expect(api.executionCurrencyHistory).toHaveBeenCalledTimes(2);
  },
);

it.each(['UNKNOWN', 'MIXED'] as const)(
  'replaces a stale inherited hint with the fresh %s result without inventing or writing a currency',
  async (source) => {
    api.executionCurrencyHistory.mockResolvedValue({
      current: null,
      history: [],
      currency_resolution: {
        currency_code: null,
        source,
        source_execution_ids: ['buy-with-gap'],
        confirmation_ids: [],
      },
    });
    render(
      <ExecutionCurrencyPanel
        tradeId="trade"
        executionId="sell"
        resolution={{
          currency_code: 'EUR',
          source: 'PRIOR_BUYS',
          source_execution_ids: ['old-buy'],
          confirmation_ids: ['old-confirmation'],
        }}
      />,
    );
    expect(screen.getByText('EUR · aus vorherigen Käufen übernommen')).toBeVisible();
    fireEvent.click(screen.getByRole('button', { name: 'Währungsherkunft ansehen' }));
    await screen.findByRole('form', { name: 'Ausführungswährung bestätigen' });
    expect(screen.queryByText('EUR · aus vorherigen Käufen übernommen')).not.toBeInTheDocument();
    expect(
      screen.getByText(source === 'UNKNOWN' ? 'unbekannt' : 'widersprüchliche Kaufwährungen'),
    ).toBeVisible();
    expect(screen.getByLabelText('Ausführungswährung (Code)')).toHaveValue('');
    expect(api.confirmExecutionCurrency).not.toHaveBeenCalled();
  },
);

it('does not save an invalid explicitly entered replacement code', async () => {
  render(<ExecutionCurrencyPanel tradeId="trade" executionId="buy" />);
  await open();
  affirm('EU');
  fireEvent.click(screen.getByRole('button', { name: 'Währungsbestätigung speichern' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('dreistelligen Währungscode');
  expect(api.confirmExecutionCurrency).not.toHaveBeenCalled();
});

it('opens the selected editor with blank new evidence and publishes dirty and pending state synchronously through both readbacks', async () => {
  const current = { ...currencyConfirmation('buy'), note: 'Alter Beleg' };
  const receipt = { ...current, id: 'usd-receipt', currency_code: 'USD', note: null };
  const saved = deferred<ExecutionCurrencyConfirmation>();
  const historyRead = deferred<ExecutionCurrencyHistory>();
  const pageRead = deferred<void>();
  const pending = vi.fn();
  const close = vi.fn();
  const onChanged = vi.fn(() => pageRead.promise);
  api.executionCurrencyHistory
    .mockResolvedValueOnce({ current, history: [current] })
    .mockReturnValueOnce(historyRead.promise);
  api.confirmExecutionCurrency.mockImplementation(() => {
    expect(pending).toHaveBeenLastCalledWith({ dirty: true, busy: true, writeBlocked: true });
    return saved.promise;
  });
  render(
    <ExecutionCurrencyPanel
      tradeId="trade"
      executionId="buy"
      editor
      confirmation={current}
      onPendingChange={pending}
      onChanged={onChanged}
      onClose={close}
    />,
  );
  await screen.findByRole('form', { name: 'Ausführungswährung bestätigen' });
  expect(screen.getByLabelText('Ausführungswährung (Code)')).toHaveValue('');
  expect(screen.getByLabelText('Beleg / Erläuterung (optional)')).toHaveValue('');
  affirm('USD');
  expect(pending).toHaveBeenLastCalledWith({ dirty: true, busy: false, writeBlocked: false });
  fireEvent.submit(screen.getByRole('form', { name: 'Ausführungswährung bestätigen' }));
  fireEvent.click(screen.getByRole('button', { name: 'Buchungseditor schließen' }));
  expect(close).not.toHaveBeenCalled();
  await act(async () => {
    saved.resolve(receipt);
    await saved.promise;
  });
  expect(onChanged).toHaveBeenCalledOnce();
  expect(pending).toHaveBeenLastCalledWith({ dirty: false, busy: true, writeBlocked: true });
  await act(async () => {
    historyRead.resolve({ current: receipt, history: [current, receipt] });
    await historyRead.promise;
  });
  expect(screen.getByRole('button', { name: 'Buchungseditor schließen' })).toBeDisabled();
  expect(pending).toHaveBeenLastCalledWith({ dirty: false, busy: true, writeBlocked: true });
  await act(async () => {
    pageRead.resolve();
    await pageRead.promise;
  });
  expect(pending).toHaveBeenLastCalledWith({ dirty: false, busy: false, writeBlocked: false });
  fireEvent.click(screen.getByRole('button', { name: 'Buchungseditor schließen' }));
  expect(close).toHaveBeenCalledOnce();
  expect(api.confirmExecutionCurrency).toHaveBeenCalledOnce();
});

it('asks the owning guard before dropping an explicit draft to reload a changed BUY source', async () => {
  const prior: ExecutionCurrencyResolution = {
    currency_code: 'EUR',
    source: 'PRIOR_BUYS',
    source_execution_ids: ['original-buy'],
    confirmation_ids: ['eur-evidence'],
  };
  const next = { ...prior, currency_code: 'CHF', confirmation_ids: ['chf-evidence'] };
  api.executionCurrencyHistory.mockResolvedValue({
    current: null,
    history: [],
    currency_resolution: prior,
  });
  const pending = vi.fn();
  const requestChange = vi.fn<(action: () => void) => void>();
  const { rerender } = render(
    <ExecutionCurrencyPanel
      tradeId="trade"
      executionId="sell"
      editor
      resolution={prior}
      requestChange={requestChange}
      onPendingChange={pending}
    />,
  );
  fireEvent.click(await screen.findByRole('button', { name: 'Abweichende Währung angeben' }));
  affirm('USD');
  rerender(
    <ExecutionCurrencyPanel
      tradeId="trade"
      executionId="sell"
      editor
      resolution={next}
      requestChange={requestChange}
      onPendingChange={pending}
    />,
  );
  expect(await screen.findByRole('alert')).toHaveTextContent('Währungsquellen dieser Buchung');
  expect(pending).toHaveBeenLastCalledWith({ dirty: true, busy: false, writeBlocked: true });
  expect(screen.queryByRole('form')).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Währungsherkunft neu laden' }));
  expect(requestChange).toHaveBeenCalledOnce();
  expect(api.executionCurrencyHistory).toHaveBeenCalledOnce();
  expect(pending).toHaveBeenLastCalledWith({ dirty: true, busy: false, writeBlocked: true });
  api.executionCurrencyHistory.mockResolvedValue({
    current: null,
    history: [],
    currency_resolution: next,
  });
  act(() => requestChange.mock.calls[0][0]());
  await screen.findByText('CHF · aus vorherigen Käufen übernommen');
  expect(pending).toHaveBeenLastCalledWith({ dirty: false, busy: false, writeBlocked: false });
  fireEvent.click(screen.getByRole('button', { name: 'Abweichende Währung angeben' }));
  expect(screen.getByLabelText('Ausführungswährung (Code)')).toHaveValue('');
  expect(api.confirmExecutionCurrency).not.toHaveBeenCalled();
});

it('freezes an uncertain currency declaration and permits only its identical explicit retry until a conscious reload', async () => {
  const pending = vi.fn();
  const onChanged = vi.fn().mockResolvedValue(undefined);
  api.confirmExecutionCurrency.mockRejectedValue(new Error('Antwort verloren'));
  render(
    <ExecutionCurrencyPanel
      tradeId="trade"
      executionId="buy"
      editor
      onPendingChange={pending}
      onChanged={onChanged}
    />,
  );
  await screen.findByRole('form', { name: 'Ausführungswährung bestätigen' });
  affirm('USD');
  fireEvent.change(screen.getByLabelText('Beleg / Erläuterung (optional)'), {
    target: { value: 'Abrechnung USD' },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Währungsbestätigung speichern' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Nur derselbe unveränderte Versuch');
  expect(screen.getByLabelText('Ausführungswährung (Code)')).toBeDisabled();
  expect(screen.getByLabelText('Beleg / Erläuterung (optional)')).toBeDisabled();
  expect(pending).toHaveBeenLastCalledWith({ dirty: true, busy: false, writeBlocked: true });
  // Even a dispatched change cannot alter the uncertain command's payload.
  affirm('CHF');
  expect(screen.getByLabelText('Ausführungswährung (Code)')).toHaveValue('USD');
  fireEvent.click(screen.getByRole('button', { name: 'Währungsbestätigung speichern' }));
  await waitFor(() => expect(api.confirmExecutionCurrency).toHaveBeenCalledTimes(2));
  expect(api.confirmExecutionCurrency.mock.calls[1]).toEqual(
    api.confirmExecutionCurrency.mock.calls[0],
  );
  await waitFor(() =>
    expect(screen.getByRole('button', { name: 'Währungsherkunft neu laden' })).toBeEnabled(),
  );
  fireEvent.click(screen.getByRole('button', { name: 'Währungsherkunft neu laden' }));
  await waitFor(() => expect(onChanged).toHaveBeenCalledOnce());
  expect(screen.getByLabelText('Ausführungswährung (Code)')).toHaveValue('');
  expect(screen.getByText(/Währungsherkunft und Buchungsstand wurden neu gelesen/)).toBeVisible();
  expect(screen.queryByText(/Gespeicherte Bestätigung und Buchungsstand/)).not.toBeInTheDocument();
  expect(pending).toHaveBeenLastCalledWith({ dirty: false, busy: false, writeBlocked: false });
  expect(api.confirmExecutionCurrency).toHaveBeenCalledTimes(2);
});

it('refreshes dependent bookings after a confirmed write even if its own history read fails and recovers without another POST', async () => {
  const receipt = currencyConfirmation('buy');
  const onChanged = vi.fn().mockResolvedValue(undefined);
  const pending = vi.fn();
  api.executionCurrencyHistory
    .mockResolvedValueOnce({ current: null, history: [] })
    .mockRejectedValueOnce(new Error('History unavailable'))
    .mockResolvedValue({ current: receipt, history: [receipt] });
  render(
    <ExecutionCurrencyPanel
      tradeId="trade"
      executionId="buy"
      editor
      onChanged={onChanged}
      onPendingChange={pending}
    />,
  );
  await screen.findByRole('form', { name: 'Ausführungswährung bestätigen' });
  affirm();
  fireEvent.click(screen.getByRole('button', { name: 'Währungsbestätigung speichern' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Speicherung bestätigt');
  expect(onChanged).toHaveBeenCalledOnce();
  expect(pending).toHaveBeenLastCalledWith({ dirty: false, busy: false, writeBlocked: true });
  fireEvent.click(screen.getByRole('button', { name: 'Währungsherkunft neu laden' }));
  await screen.findByText('Gespeicherte Bestätigung und Buchungsstand wurden neu gelesen.');
  expect(onChanged).toHaveBeenCalledTimes(2);
  expect(api.confirmExecutionCurrency).toHaveBeenCalledOnce();
  expect(pending).toHaveBeenLastCalledWith({ dirty: false, busy: false, writeBlocked: false });
});

it('keeps further confirmation blocked when the page projection read fails after a successful history read', async () => {
  const receipt = currencyConfirmation('buy');
  const onChanged = vi
    .fn()
    .mockRejectedValueOnce(new Error('Position unavailable'))
    .mockResolvedValue(undefined);
  const pending = vi.fn();
  api.executionCurrencyHistory
    .mockResolvedValueOnce({ current: null, history: [] })
    .mockResolvedValue({ current: receipt, history: [receipt] });
  render(
    <ExecutionCurrencyPanel
      tradeId="trade"
      executionId="buy"
      editor
      onChanged={onChanged}
      onPendingChange={pending}
    />,
  );
  await screen.findByRole('form', { name: 'Ausführungswährung bestätigen' });
  affirm();
  fireEvent.click(screen.getByRole('button', { name: 'Währungsbestätigung speichern' }));
  await screen.findByText(/Die übrigen Buchungen konnten noch nicht aktualisiert/);
  expect(screen.getByLabelText('Ausführungswährung (Code)')).toBeDisabled();
  expect(pending).toHaveBeenLastCalledWith({ dirty: false, busy: false, writeBlocked: true });
  fireEvent.click(screen.getByRole('button', { name: 'Währungsherkunft neu laden' }));
  await screen.findByText('Gespeicherte Bestätigung und Buchungsstand wurden neu gelesen.');
  expect(screen.getByLabelText('Ausführungswährung (Code)')).toBeEnabled();
  expect(api.confirmExecutionCurrency).toHaveBeenCalledOnce();
});

it('does not clear a new A attempt key when a prior A write returns after A to B to A navigation', async () => {
  const oldWrite = deferred<ExecutionCurrencyConfirmation>();
  const pending = vi.fn();
  api.confirmExecutionCurrency
    .mockReturnValueOnce(oldWrite.promise)
    .mockRejectedValue(new Error('Neue Antwort verloren'));
  const { rerender } = render(
    <ExecutionCurrencyPanel tradeId="A" executionId="buy" editor onPendingChange={pending} />,
  );
  await screen.findByRole('form', { name: 'Ausführungswährung bestätigen' });
  affirm();
  fireEvent.click(screen.getByRole('button', { name: 'Währungsbestätigung speichern' }));
  rerender(<ExecutionCurrencyPanel tradeId="B" executionId="other-buy" editor />);
  await screen.findByRole('form', { name: 'Ausführungswährung bestätigen' });
  rerender(
    <ExecutionCurrencyPanel tradeId="A" executionId="buy" editor onPendingChange={pending} />,
  );
  await screen.findByRole('form', { name: 'Ausführungswährung bestätigen' });
  affirm('USD');
  fireEvent.click(screen.getByRole('button', { name: 'Währungsbestätigung speichern' }));
  await screen.findByRole('alert');
  const currentAttempt = api.confirmExecutionCurrency.mock.calls[1];
  await act(async () => {
    oldWrite.resolve(currencyConfirmation('buy'));
    await oldWrite.promise;
  });
  expect(screen.queryByText(/Währung bestätigt. Eine erneute/)).not.toBeInTheDocument();
  expect(pending).toHaveBeenLastCalledWith({ dirty: true, busy: false, writeBlocked: true });
  fireEvent.click(screen.getByRole('button', { name: 'Währungsbestätigung speichern' }));
  await waitFor(() => expect(api.confirmExecutionCurrency).toHaveBeenCalledTimes(3));
  expect(api.confirmExecutionCurrency.mock.calls[2]).toEqual(currentAttempt);
});

it('keeps the draft pinned through a temporary timeline write block and removes writes when its execution is replaced', async () => {
  const { rerender } = render(<ExecutionCurrencyPanel tradeId="trade" executionId="buy" editor />);
  await screen.findByRole('form', { name: 'Ausführungswährung bestätigen' });
  affirm('USD');
  rerender(<ExecutionCurrencyPanel tradeId="trade" executionId="buy" editor disabled />);
  expect(screen.getByLabelText('Ausführungswährung (Code)')).toHaveValue('USD');
  expect(screen.getByRole('button', { name: 'Währungsbestätigung speichern' })).toBeDisabled();
  fireEvent.submit(screen.getByRole('form', { name: 'Ausführungswährung bestätigen' }));
  expect(api.confirmExecutionCurrency).not.toHaveBeenCalled();
  rerender(<ExecutionCurrencyPanel tradeId="trade" executionId="buy" editor />);
  expect(screen.getByLabelText('Ausführungswährung (Code)')).toHaveValue('USD');
  expect(screen.getByRole('button', { name: 'Währungsbestätigung speichern' })).toBeEnabled();
  rerender(<ExecutionCurrencyPanel tradeId="trade" executionId="buy" editor readOnly />);
  expect(screen.queryByRole('form')).not.toBeInTheDocument();
  expect(screen.getByText('Keine Bestätigungen gespeichert.')).toBeInTheDocument();
  expect(api.executionCurrencyHistory).toHaveBeenCalledOnce();
  expect(api.confirmExecutionCurrency).not.toHaveBeenCalled();
});

it('allows closing after an initial read failure without declaring an uncertain write', async () => {
  api.executionCurrencyHistory.mockRejectedValue(new Error('History unavailable'));
  const pending = vi.fn();
  const close = vi.fn();
  render(
    <ExecutionCurrencyPanel
      tradeId="trade"
      executionId="buy"
      editor
      onClose={close}
      onPendingChange={pending}
    />,
  );
  expect(await screen.findByRole('alert')).toHaveTextContent('History unavailable');
  expect(pending).toHaveBeenLastCalledWith({ dirty: false, busy: false, writeBlocked: false });
  fireEvent.click(screen.getByRole('button', { name: 'Buchungseditor schließen' }));
  expect(close).toHaveBeenCalledOnce();
  expect(api.confirmExecutionCurrency).not.toHaveBeenCalled();
});

it('checks the shared write lock synchronously even before disabled props can render', async () => {
  let anotherWritePending = false;
  const pending = vi.fn();
  render(
    <ExecutionCurrencyPanel
      tradeId="trade"
      executionId="buy"
      editor
      isWriteBlocked={() => anotherWritePending}
      onPendingChange={pending}
    />,
  );
  await screen.findByRole('form', { name: 'Ausführungswährung bestätigen' });
  affirm('USD');
  anotherWritePending = true;
  // The old rendered button still appears enabled; the synchronous predicate owns safety.
  expect(screen.getByRole('button', { name: 'Währungsbestätigung speichern' })).toBeEnabled();
  fireEvent.submit(screen.getByRole('form', { name: 'Ausführungswährung bestätigen' }));
  expect(api.confirmExecutionCurrency).not.toHaveBeenCalled();
  expect(screen.getByLabelText('Ausführungswährung (Code)')).toHaveValue('USD');
  expect(pending).toHaveBeenLastCalledWith({ dirty: true, busy: false, writeBlocked: false });
  anotherWritePending = false;
  fireEvent.submit(screen.getByRole('form', { name: 'Ausführungswährung bestätigen' }));
  await waitFor(() => expect(api.confirmExecutionCurrency).toHaveBeenCalledOnce());
  expect(api.confirmExecutionCurrency.mock.calls[0][2]).toMatchObject({ currency_code: 'USD' });
});
