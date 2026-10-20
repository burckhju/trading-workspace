import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { currencyConfirmation } from '../../../test/realizedGrossFixtures';
import { tradeManagementApiClient } from '../services/client';
import type { ExecutionCurrencyResolution, TradeTimelineEntryResponse } from '../types/api';
import { ExecutionDatesPanel } from './ExecutionDatesPanel';

vi.mock('../services/client', () => ({
  tradeTimelineChangedEvent: 'trade-timeline-changed',
  tradeManagementApiClient: {
    timeline: vi.fn(),
    correctExecution: vi.fn(),
    executionCurrencyHistory: vi.fn(),
    confirmExecutionCurrency: vi.fn(),
  },
}));
const api = vi.mocked(tradeManagementApiClient);
const buy: TradeTimelineEntryResponse = {
  id: 'buy',
  trade_id: 'trade',
  kind: 'EXECUTION',
  execution_side: 'BUY',
  quantity: 10,
  price_per_unit: '0.550000',
  occurred_at: '2026-08-16T22:00:00Z',
  recorded_at: '2026-09-12T17:00:00Z',
  executed_on: '2026-08-17',
  execution_timezone: 'Europe/Berlin',
  management_event_type: null,
  numeric_value: null,
  text_value: null,
  supersedes_id: null,
};
const sale = { ...buy, id: 'sale', execution_side: 'SELL' as const, executed_on: '2026-08-22' };
const onChanged = vi.fn<() => Promise<void>>();

beforeEach(() => {
  vi.resetAllMocks();
  api.timeline.mockResolvedValue([buy, sale]);
  api.correctExecution.mockResolvedValue({} as never);
  onChanged.mockResolvedValue(undefined);
});
async function open(side = 'Kaufdatum') {
  await screen.findByRole('button', { name: `${side} korrigieren` });
  fireEvent.click(screen.getByRole('button', { name: `${side} korrigieren` }));
  return screen.getByRole('form', { name: 'Ausführungsdatum korrigieren' });
}
function confirm() {
  fireEvent.click(
    screen.getByRole('checkbox', {
      name: 'Ich bestätige das tatsächliche Ausführungsdatum dieser Buchung.',
    }),
  );
}

it.each([
  ['Kaufdatum', buy, '2026-08-16'],
  ['Verkaufsdatum', sale, '2026-08-23'],
])('corrects existing %s, not another execution or a new BUY/SELL', async (label, row, date) => {
  render(<ExecutionDatesPanel tradeId="trade" onChanged={onChanged} />);
  const form = await open(label);
  const field = within(form).getByLabelText(`${label} korrigieren`);
  expect(field).toHaveValue(row.executed_on);
  expect(within(form).getByRole('button', { name: 'Datumsänderung speichern' })).toBeDisabled();
  fireEvent.change(field, { target: { value: date } });
  confirm();
  api.timeline.mockResolvedValue([
    buy,
    sale,
    { ...row, id: 'corrected', executed_on: date, supersedes_id: row.id },
  ]);
  fireEvent.click(screen.getByRole('button', { name: 'Datumsänderung speichern' }));
  await screen.findByText(/Datum korrigiert/);
  expect(api.correctExecution).toHaveBeenCalledExactlyOnceWith('trade', row.id, {
    side: row.execution_side,
    quantity: row.quantity,
    price_per_unit: row.price_per_unit,
    executed_on: date,
    execution_timezone: 'Europe/Berlin',
  });
  await waitFor(() => expect(onChanged).toHaveBeenCalledOnce());
  await waitFor(() => expect(screen.queryByRole('form')).not.toBeInTheDocument());
});

it('requires a changed value plus confirmation and supports cancelling without a write', async () => {
  render(<ExecutionDatesPanel tradeId="trade" onChanged={onChanged} />);
  await open();
  confirm();
  expect(screen.getByRole('button', { name: 'Datumsänderung speichern' })).toBeDisabled();
  fireEvent.change(screen.getByLabelText('Kaufdatum korrigieren'), {
    target: { value: '2026-08-16' },
  });
  expect(
    screen.getByRole('checkbox', {
      name: 'Ich bestätige das tatsächliche Ausführungsdatum dieser Buchung.',
    }),
  ).not.toBeChecked();
  fireEvent.click(screen.getByRole('button', { name: 'Abbrechen' }));
  expect(screen.queryByRole('form')).not.toBeInTheDocument();
  expect(api.correctExecution).not.toHaveBeenCalled();
});

it('keeps cancelled history read-only', async () => {
  render(<ExecutionDatesPanel tradeId="trade" cancelled onChanged={onChanged} />);
  await screen.findByText(/Kaufdatum · 10 Stück/);
  expect(screen.getByText(/schreibgeschützt/)).toBeVisible();
  expect(screen.queryByRole('button', { name: /korrigieren/ })).not.toBeInTheDocument();
});

it('retains the evidenced original currency through the owner when only the date is corrected', async () => {
  api.timeline.mockResolvedValue([
    {
      ...buy,
      currency_confirmation: {
        id: 'old-confirmation',
        execution_id: buy.id,
        currency_code: 'EUR',
        source: 'USER_CONFIRMED',
        note: 'Old evidence',
        confirmed_at: '2026-08-17T10:00:00Z',
        confirmed_by: 'test',
        supersedes_confirmation_id: null,
      },
    },
  ]);
  render(<ExecutionDatesPanel tradeId="trade" onChanged={onChanged} />);
  const form = await open();
  expect(within(form).queryByLabelText('Ausführungswährung (Code)')).not.toBeInTheDocument();
  expect(within(form).getByText('Währung: EUR · ausdrücklich bestätigt')).toBeVisible();
  fireEvent.change(within(form).getByLabelText('Kaufdatum korrigieren'), {
    target: { value: '2026-08-16' },
  });
  confirm();
  fireEvent.click(within(form).getByRole('button', { name: 'Datumsänderung speichern' }));
  await screen.findByText(/Datum korrigiert/);
  expect(api.correctExecution).toHaveBeenCalledWith('trade', 'buy', {
    side: 'BUY',
    quantity: buy.quantity,
    price_per_unit: buy.price_per_unit,
    executed_on: '2026-08-16',
    execution_timezone: 'Europe/Berlin',
  });
});

it('can deliberately state a different correction currency while preserving the separate date confirmation', async () => {
  render(<ExecutionDatesPanel tradeId="trade" onChanged={onChanged} />);
  const form = within(await open());
  fireEvent.change(form.getByLabelText('Kaufdatum korrigieren'), {
    target: { value: '2026-08-16' },
  });
  fireEvent.click(form.getByRole('button', { name: 'Abweichende Währung angeben' }));
  fireEvent.change(form.getByLabelText('Ausführungswährung (Code)'), { target: { value: 'USD' } });
  expect(form.getAllByRole('checkbox')).toHaveLength(1);
  expect(form.getByRole('button', { name: 'Datumsänderung speichern' })).toBeDisabled();
  confirm();
  fireEvent.click(form.getByRole('button', { name: 'Datumsänderung speichern' }));
  await screen.findByText(/Datum korrigiert/);
  expect(api.correctExecution).toHaveBeenCalledExactlyOnceWith('trade', buy.id, {
    side: 'BUY',
    quantity: buy.quantity,
    price_per_unit: buy.price_per_unit,
    executed_on: '2026-08-16',
    execution_timezone: 'Europe/Berlin',
    currency_confirmation: { currency_code: 'USD', source: 'USER_CONFIRMED', note: null },
  });
});

it('retains precise time by default and makes changing to date-only explicit', async () => {
  api.timeline.mockResolvedValue([
    {
      ...buy,
      executed_on: null,
      execution_timezone: null,
      occurred_at: '2026-08-17T08:30:01.123456Z',
    },
  ]);
  render(<ExecutionDatesPanel tradeId="trade" onChanged={onChanged} />);
  await open();
  expect(screen.getByRole('checkbox', { name: /Bisherige Uhrzeit beibehalten/ })).toBeChecked();
  fireEvent.click(screen.getByRole('checkbox', { name: /Bisherige Uhrzeit beibehalten/ }));
  expect(screen.getByText(/genaue Uhrzeit gilt als unbekannt/)).toBeVisible();
  confirm();
  fireEvent.click(screen.getByRole('button', { name: 'Datumsänderung speichern' }));
  await screen.findByText(/Datum korrigiert/);
  expect(api.correctExecution).toHaveBeenCalledWith(
    'trade',
    'buy',
    expect.objectContaining({ executed_on: '2026-08-17' }),
  );
});

it('does not offer superseded versions and detects a concurrent replacement before another write', async () => {
  api.timeline.mockResolvedValue([buy, { ...buy, id: 'new', supersedes_id: 'buy' }]);
  render(<ExecutionDatesPanel tradeId="trade" onChanged={onChanged} />);
  await open();
  expect(screen.getAllByRole('button', { name: 'Kaufdatum korrigieren' })).toHaveLength(1);
  api.timeline.mockResolvedValue([
    buy,
    { ...buy, id: 'new', supersedes_id: 'buy' },
    { ...buy, id: 'newest', supersedes_id: 'new' },
  ]);
  fireEvent.click(screen.getByRole('button', { name: 'Buchungsdaten neu laden' }));
  await screen.findByText(/Diese Buchung wurde bereits ersetzt/);
  expect(screen.getByRole('button', { name: 'Datumsänderung speichern' })).toBeDisabled();
  expect(api.correctExecution).not.toHaveBeenCalled();
});

it('handles API/chronology errors without claiming success or discarding the entered date', async () => {
  api.correctExecution.mockRejectedValue(new Error('Verkauf liegt vor dem Kauf'));
  render(<ExecutionDatesPanel tradeId="trade" onChanged={onChanged} />);
  await open('Verkaufsdatum');
  fireEvent.change(screen.getByLabelText('Verkaufsdatum korrigieren'), {
    target: { value: '2026-08-16' },
  });
  confirm();
  fireEvent.click(screen.getByRole('button', { name: 'Datumsänderung speichern' }));
  await screen.findByText(/Korrektur nicht bestätigt: Verkauf liegt vor dem Kauf/);
  expect(screen.getByLabelText('Verkaufsdatum korrigieren')).toHaveValue('2026-08-16');
  expect(onChanged).not.toHaveBeenCalled();
});

it('distinguishes a successful write from a failed subsequent position refresh', async () => {
  onChanged.mockRejectedValue(new Error('Offline'));
  render(<ExecutionDatesPanel tradeId="trade" onChanged={onChanged} />);
  await open();
  fireEvent.change(screen.getByLabelText('Kaufdatum korrigieren'), {
    target: { value: '2026-08-16' },
  });
  confirm();
  fireEvent.click(screen.getByRole('button', { name: 'Datumsänderung speichern' }));
  await screen.findByText(/Datum gespeichert, Ansicht noch nicht aktualisiert/);
  expect(screen.queryByRole('form')).not.toBeInTheDocument();
});

it('reports missing data, supports reload and never supplies placeholder executions', async () => {
  api.timeline.mockRejectedValue(new Error('Nicht erreichbar'));
  render(<ExecutionDatesPanel tradeId="trade" onChanged={onChanged} />);
  await screen.findByRole('alert');
  expect(screen.queryByRole('button', { name: /korrigieren/ })).not.toBeInTheDocument();
  api.timeline.mockResolvedValue([]);
  fireEvent.click(screen.getByRole('button', { name: 'Buchungsdaten neu laden' }));
  await screen.findByText(/Keine Kauf-\/Verkaufsbuchungen vorhanden/);
});

it('refreshes dependent sale and additional BUY currency after a BUY confirmation, marks an opened stale source and preserves an unsaved date', async () => {
  let stored = false;
  const confirmation = currencyConfirmation(buy.id);
  const unknown: ExecutionCurrencyResolution = {
    currency_code: null,
    source: 'UNKNOWN',
    source_execution_ids: [],
    confirmation_ids: [],
  };
  const direct: ExecutionCurrencyResolution = {
    currency_code: 'EUR',
    source: 'USER_CONFIRMED',
    source_execution_ids: [buy.id],
    confirmation_ids: [confirmation.id],
  };
  const inherited: ExecutionCurrencyResolution = { ...direct, source: 'PRIOR_BUYS' };
  api.timeline.mockImplementation(() =>
    Promise.resolve([
      {
        ...buy,
        currency_confirmation: stored ? confirmation : null,
        currency_resolution: stored ? direct : unknown,
      },
      { ...sale, currency_confirmation: null, currency_resolution: stored ? inherited : unknown },
      {
        ...buy,
        id: 'additional-buy',
        executed_on: '2026-08-25',
        currency_confirmation: null,
        currency_resolution: stored ? inherited : unknown,
      },
    ]),
  );
  api.executionCurrencyHistory.mockImplementation((_tradeId, executionId) =>
    Promise.resolve({
      current: stored && executionId === buy.id ? confirmation : null,
      history: stored && executionId === buy.id ? [confirmation] : [],
      currency_resolution: stored ? (executionId === buy.id ? direct : inherited) : unknown,
    }),
  );
  api.confirmExecutionCurrency.mockImplementation(() => {
    stored = true;
    return Promise.resolve(confirmation);
  });
  render(<ExecutionDatesPanel tradeId="trade" onChanged={onChanged} />);
  const buyRow = within(await screen.findByRole('article', { name: 'Buchung buy' }));
  const saleRow = within(screen.getByRole('article', { name: 'Buchung sale' }));
  fireEvent.click(saleRow.getByRole('button', { name: 'Währung prüfen / bestätigen' }));
  await saleRow.findByRole('form', { name: 'Ausführungswährung bestätigen' });
  fireEvent.click(saleRow.getByRole('button', { name: 'Verkaufsdatum korrigieren' }));
  const dateForm = within(screen.getByRole('form', { name: 'Ausführungsdatum korrigieren' }));
  fireEvent.change(dateForm.getByLabelText('Verkaufsdatum korrigieren'), {
    target: { value: '2026-08-23' },
  });
  confirm();
  fireEvent.click(buyRow.getByRole('button', { name: 'Währung prüfen / bestätigen' }));
  await buyRow.findByRole('form', { name: 'Ausführungswährung bestätigen' });
  fireEvent.change(buyRow.getByLabelText('Ausführungswährung (Code)'), {
    target: { value: 'EUR' },
  });
  fireEvent.click(buyRow.getByRole('button', { name: 'Währungsbestätigung speichern' }));
  const additionalRow = within(screen.getByRole('article', { name: 'Buchung additional-buy' }));
  expect(await additionalRow.findByText('EUR · aus vorherigen Käufen übernommen')).toBeVisible();
  expect(
    additionalRow.queryByRole('button', { name: 'Währung prüfen / bestätigen' }),
  ).not.toBeInTheDocument();
  expect(await saleRow.findByRole('alert')).toHaveTextContent(
    'Währungsquellen dieser Buchung haben sich geändert',
  );
  expect(saleRow.queryByText('unbekannt')).not.toBeInTheDocument();
  expect(saleRow.queryByRole('form')).not.toBeInTheDocument();
  expect(dateForm.getByLabelText('Verkaufsdatum korrigieren')).toHaveValue('2026-08-23');
  expect(
    dateForm.getByRole('checkbox', { name: /Ich bestätige das tatsächliche Ausführungsdatum/ }),
  ).toBeChecked();
  expect(dateForm.getByText('Währung: EUR · aus vorherigen Käufen übernommen')).toBeVisible();
  fireEvent.click(saleRow.getByRole('button', { name: 'Währungsherkunft neu laden' }));
  expect(await saleRow.findByText('EUR · aus vorherigen Käufen übernommen')).toBeVisible();
  expect(saleRow.queryByRole('form')).not.toBeInTheDocument();
  expect(api.confirmExecutionCurrency).toHaveBeenCalledOnce();
  expect(api.confirmExecutionCurrency.mock.calls[0][1]).toBe(buy.id);
  expect(api.correctExecution).not.toHaveBeenCalled();
});
