import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { MarketApiError } from '../../market/services/http';
import { currencyConfirmation } from '../../../test/realizedGrossFixtures';
import { tradeManagementApiClient, tradeTimelineChangedEvent } from '../services/client';
import type {
  ExecutionCorrectionRequest,
  ExecutionCurrencyResolution,
  SaleResponse,
  TradeTimelineEntryResponse,
} from '../types/api';
import { ExecutionDatesPanel } from './ExecutionDatesPanel';
import { TradePendingChangesProvider, useTradePendingChanges } from './TradePendingChanges';

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
  price_per_unit: '0.550000000000000000000001',
  occurred_at: '2026-08-16T22:00:00Z',
  recorded_at: '2026-09-12T17:00:00.123456Z',
  executed_on: '2026-08-17',
  execution_timezone: 'Europe/Berlin',
  management_event_type: null,
  numeric_value: null,
  text_value: null,
  supersedes_id: null,
};
const sale = { ...buy, id: 'sale', execution_side: 'SELL' as const, executed_on: '2026-08-22' };
const unknown: ExecutionCurrencyResolution = {
  currency_code: null,
  source: 'UNKNOWN',
  source_execution_ids: [],
  confirmation_ids: [],
};
const onChanged = vi.fn<() => Promise<void>>();
let timeline: TradeTimelineEntryResponse[];
function corrected(tradeId: string, id: string, payload: ExecutionCorrectionRequest): SaleResponse {
  const original = timeline.find((entry) => entry.id === id)!;
  const replacement = {
    ...original,
    id: 'corrected-' + id,
    supersedes_id: id,
    executed_on: 'executed_on' in payload ? payload.executed_on : null,
    execution_timezone: 'execution_timezone' in payload ? payload.execution_timezone : null,
    occurred_at:
      'executed_at' in payload ? payload.executed_at : payload.executed_on + 'T00:00:00Z',
    recorded_at: '2026-10-26T11:00:01.654321Z',
  };
  timeline = [...timeline, replacement];
  return {
    execution: { id: replacement.id, trade_id: tradeId },
    position: { trade_id: tradeId },
  } as SaleResponse;
}
function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (cause: unknown) => void;
  const promise = new Promise<T>((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, resolve, reject };
}
function ExternalWriter({ state }: { state: { busy: boolean } }) {
  useTradePendingChanges('other-write', {
    isDirty: () => false,
    isBusy: () => state.busy,
    onDiscard: () => undefined,
  });
  return null;
}
beforeEach(() => {
  vi.resetAllMocks();
  sessionStorage.clear();
  timeline = [buy, sale];
  api.timeline.mockImplementation(() => Promise.resolve([...timeline]));
  api.correctExecution.mockImplementation((tradeId, id, payload) =>
    Promise.resolve(corrected(tradeId, id, payload)),
  );
  api.executionCurrencyHistory.mockResolvedValue({
    current: null,
    history: [],
    currency_resolution: unknown,
  });
  onChanged.mockResolvedValue(undefined);
});
async function open(side = 'Kaufdatum') {
  fireEvent.click(await screen.findByRole('button', { name: side + ' korrigieren' }));
  return screen.getByRole('form', { name: 'Ausführungsdatum korrigieren' });
}
function confirm() {
  fireEvent.click(
    screen.getByRole('checkbox', {
      name: 'Ich bestätige das tatsächliche Ausführungsdatum dieser Buchung.',
    }),
  );
}
function changeDate(value = '2026-08-16', side = 'Kaufdatum') {
  fireEvent.change(screen.getByLabelText(side + ' korrigieren'), { target: { value } });
}
function save() {
  fireEvent.click(screen.getByRole('button', { name: 'Datumsänderung speichern' }));
}
function changed() {
  act(() => {
    window.dispatchEvent(
      new CustomEvent(tradeTimelineChangedEvent, { detail: { tradeId: 'trade' } }),
    );
  });
}
async function discard() {
  fireEvent.click(await screen.findByRole('button', { name: 'Eingaben verwerfen und wechseln' }));
}

it.each([
  ['Kaufdatum', buy, '2026-08-16'],
  ['Verkaufsdatum', sale, '2026-08-23'],
] as const)(
  'edits the selected %s inline and preserves side, quantity and the complete decimal',
  async (label, row, date) => {
    render(<ExecutionDatesPanel tradeId="trade" onChanged={onChanged} />);
    const form = await open(label);
    expect(
      within(screen.getByRole('article', { name: 'Buchung ' + row.id })).getByRole('form'),
    ).toBe(form);
    expect(within(form).getByLabelText(label + ' korrigieren')).toHaveValue(row.executed_on);
    expect(
      within(screen.getByRole('article', { name: 'Buchung ' + row.id })).queryByText(
        /^Ausgeführt:/,
      ),
    ).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Datumsänderung speichern' })).toBeDisabled();
    changeDate(date, label);
    confirm();
    save();
    await screen.findByText(/Datum korrigiert/);
    expect(api.correctExecution).toHaveBeenCalledExactlyOnceWith('trade', row.id, {
      side: row.execution_side,
      quantity: row.quantity,
      price_per_unit: row.price_per_unit,
      executed_on: date,
      execution_timezone: 'Europe/Berlin',
    });
    expect(onChanged).toHaveBeenCalledOnce();
    expect(screen.queryByRole('form')).not.toBeInTheDocument();
    expect(screen.queryByRole('article', { name: 'Buchung ' + row.id })).not.toBeInTheDocument();
    expect(screen.getByRole('article', { name: 'Buchung corrected-' + row.id })).toBeVisible();
  },
);

it('has one current list or one read-only history with full correction references and timestamps', async () => {
  const replacement = { ...buy, id: 'replacement-full-id', supersedes_id: buy.id };
  const management: TradeTimelineEntryResponse = {
    ...buy,
    id: 'management',
    kind: 'MANAGEMENT_EVENT',
    execution_side: null,
    management_event_type: 'STOP_CHANGED',
    numeric_value: '12.50',
  };
  const cancellation: TradeTimelineEntryResponse = {
    ...management,
    id: 'cancellation',
    kind: 'CANCELLATION',
    text_value: 'Duplicate',
    numeric_value: null,
  };
  timeline = [buy, replacement, sale, management, cancellation];
  render(<ExecutionDatesPanel tradeId="trade" onChanged={onChanged} />);
  await screen.findByRole('article', { name: 'Buchung replacement-full-id' });
  expect(screen.getAllByRole('article')).toHaveLength(2);
  expect(screen.queryByRole('heading', { name: 'Trade Timeline' })).not.toBeInTheDocument();
  const reads = api.timeline.mock.calls.length;
  fireEvent.click(screen.getByRole('tab', { name: 'Historie' }));
  expect(screen.queryByRole('article')).not.toBeInTheDocument();
  expect(screen.getAllByRole('listitem', { name: /Historischer Eintrag/ })).toHaveLength(5);
  expect(screen.getByText(/ersetzt buy/)).toBeVisible();
  expect(screen.getByText(/Ersetzt durch replacement-full-id/)).toBeVisible();
  expect(
    within(screen.getByRole('listitem', { name: 'Historischer Eintrag buy' })).getByText(
      /2026-09-12T17:00:00.123456Z/,
    ),
  ).toBeVisible();
  expect(screen.getByText('Fehleingabe storniert (kein Verkauf)')).toBeVisible();
  expect(screen.queryByRole('button', { name: /korrigieren|bestätigen/ })).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('tab', { name: 'Aktuelle Buchungen' }));
  expect(screen.getAllByRole('article')).toHaveLength(2);
  expect(api.timeline).toHaveBeenCalledTimes(reads);
});

it('requires a changed date plus explicit confirmation and guards cancellation without writing', async () => {
  render(<ExecutionDatesPanel tradeId="trade" onChanged={onChanged} />);
  await open();
  confirm();
  expect(screen.getByRole('button', { name: 'Datumsänderung speichern' })).toBeDisabled();
  changeDate();
  expect(screen.getByRole('checkbox', { name: /Ich bestätige/ })).not.toBeChecked();
  fireEvent.click(screen.getByRole('button', { name: 'Abbrechen' }));
  expect(screen.getByRole('alertdialog')).toBeVisible();
  fireEvent.click(screen.getByRole('button', { name: 'Hier bleiben' }));
  expect(screen.getByLabelText('Kaufdatum korrigieren')).toHaveValue('2026-08-16');
  fireEvent.click(screen.getByRole('button', { name: 'Abbrechen' }));
  await discard();
  expect(screen.queryByRole('form')).not.toBeInTheDocument();
  expect(api.correctExecution).not.toHaveBeenCalled();
  expect(screen.getByRole('region', { name: 'Kauf- und Verkaufsdaten' })).toHaveFocus();
});

it('guards booking, editor and history changes and only mounts one editor', async () => {
  render(<ExecutionDatesPanel tradeId="trade" onChanged={onChanged} />);
  await open();
  changeDate();
  fireEvent.click(screen.getByRole('button', { name: 'Verkaufsdatum korrigieren' }));
  await discard();
  expect(screen.getAllByRole('form')).toHaveLength(1);
  expect(screen.getByLabelText('Verkaufsdatum korrigieren')).toHaveValue(sale.executed_on);
  const saleRow = within(screen.getByRole('article', { name: 'Buchung sale' }));
  fireEvent.click(saleRow.getByRole('button', { name: 'Währung prüfen / bestätigen' }));
  const currency = await screen.findByRole('form', { name: 'Ausführungswährung bestätigen' });
  expect(screen.getAllByRole('form')).toHaveLength(1);
  expect(
    screen.queryByRole('form', { name: 'Ausführungsdatum korrigieren' }),
  ).not.toBeInTheDocument();
  fireEvent.change(within(currency).getByLabelText('Ausführungswährung (Code)'), {
    target: { value: 'EUR' },
  });
  fireEvent.click(screen.getByRole('tab', { name: 'Historie' }));
  fireEvent.click(screen.getByRole('button', { name: 'Hier bleiben' }));
  expect(screen.getByLabelText('Ausführungswährung (Code)')).toHaveValue('EUR');
  fireEvent.click(screen.getByRole('tab', { name: 'Historie' }));
  await discard();
  expect(screen.getByRole('heading', { name: 'Trade Timeline' })).toBeVisible();
  expect(screen.queryByRole('form')).not.toBeInTheDocument();
  expect(api.correctExecution).not.toHaveBeenCalled();
  expect(api.confirmExecutionCurrency).not.toHaveBeenCalled();
});

it('keeps cancelled current bookings and history read-only', async () => {
  render(<ExecutionDatesPanel tradeId="trade" cancelled onChanged={onChanged} />);
  await screen.findByText(/Kaufdatum · 10 Stück/);
  expect(screen.getByText(/schreibgeschützt/)).toBeVisible();
  expect(screen.queryByRole('button', { name: /korrigieren|bestätigen/ })).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('tab', { name: 'Historie' }));
  expect(screen.getAllByRole('listitem', { name: /Historischer Eintrag/ })).toHaveLength(2);
});

it('reuses the evidenced original currency without copying an old note or confirmation', async () => {
  timeline = [
    {
      ...buy,
      currency_confirmation: { ...currencyConfirmation(buy.id), note: 'Original evidence' },
    },
  ];
  render(<ExecutionDatesPanel tradeId="trade" onChanged={onChanged} />);
  const form = await open();
  expect(within(form).queryByLabelText('Ausführungswährung (Code)')).not.toBeInTheDocument();
  expect(within(form).getByText('Währung: EUR · ausdrücklich bestätigt')).toBeVisible();
  changeDate();
  confirm();
  save();
  await screen.findByText(/Datum korrigiert/);
  expect(api.correctExecution.mock.calls[0][2]).not.toHaveProperty('currency_confirmation');
  expect(api.confirmExecutionCurrency).not.toHaveBeenCalled();
});

it('uses one correction POST for changed date with an explicitly different currency', async () => {
  render(<ExecutionDatesPanel tradeId="trade" onChanged={onChanged} />);
  const form = within(await open());
  changeDate();
  fireEvent.click(form.getByRole('button', { name: 'Abweichende Währung angeben' }));
  fireEvent.change(form.getByLabelText('Ausführungswährung (Code)'), { target: { value: 'USD' } });
  expect(form.getByRole('button', { name: 'Datumsänderung speichern' })).toBeDisabled();
  confirm();
  save();
  await screen.findByText(/Datum korrigiert/);
  expect(api.correctExecution).toHaveBeenCalledExactlyOnceWith('trade', buy.id, {
    side: 'BUY',
    quantity: buy.quantity,
    price_per_unit: buy.price_per_unit,
    executed_on: '2026-08-16',
    execution_timezone: 'Europe/Berlin',
    currency_confirmation: { currency_code: 'USD', source: 'USER_CONFIRMED', note: null },
  });
  expect(api.confirmExecutionCurrency).not.toHaveBeenCalled();
});

it('keeps every fractional second by default and makes date-only conversion explicit', async () => {
  timeline = [
    {
      ...buy,
      executed_on: null,
      execution_timezone: null,
      occurred_at: '2026-08-17T08:30:01.123456Z',
    },
  ];
  render(<ExecutionDatesPanel tradeId="trade" onChanged={onChanged} />);
  await open();
  expect(screen.getByRole('checkbox', { name: /Bisherige Uhrzeit beibehalten/ })).toBeChecked();
  changeDate('2026-08-18');
  confirm();
  save();
  await screen.findByText(/Datum korrigiert/);
  const precisePayload = api.correctExecution.mock.calls[0][2];
  expect('executed_at' in precisePayload && precisePayload.executed_at).toMatch(
    /T08:30:01\.123456Z$/,
  );
  await open();
  fireEvent.click(screen.getByRole('checkbox', { name: /Bisherige Uhrzeit beibehalten/ }));
  expect(screen.getByText(/genaue Uhrzeit gilt als unbekannt/)).toBeVisible();
  confirm();
  save();
  await screen.findByText(/Datum korrigiert/);
  expect(api.correctExecution.mock.calls[1][2]).toHaveProperty('executed_on', '2026-08-18');
  expect(api.correctExecution.mock.calls[1][2]).not.toHaveProperty('executed_at');
});

it('retains a replaced date editor as stale without counting it as a current execution or rebinding', async () => {
  timeline = [buy];
  render(<ExecutionDatesPanel tradeId="trade" onChanged={onChanged} />);
  await open();
  changeDate();
  timeline = [buy, { ...buy, id: 'new', supersedes_id: buy.id }];
  changed();
  await screen.findByText(/Diese Buchung wurde bereits ersetzt/);
  expect(screen.getByLabelText('Kaufdatum korrigieren')).toHaveValue('2026-08-16');
  expect(screen.queryByRole('article', { name: 'Buchung buy' })).not.toBeInTheDocument();
  expect(screen.getByRole('article', { name: 'Ersetzte Bearbeitungsbasis' })).toBeVisible();
  expect(screen.getByRole('article', { name: 'Buchung new' })).toBeVisible();
  expect(screen.getByRole('button', { name: 'Datumsänderung speichern' })).toBeDisabled();
  expect(api.correctExecution).not.toHaveBeenCalled();
});

it('keeps the currency editor mounted and dirty when its execution becomes historical', async () => {
  render(<ExecutionDatesPanel tradeId="trade" onChanged={onChanged} />);
  const row = within(await screen.findByRole('article', { name: 'Buchung buy' }));
  fireEvent.click(row.getByRole('button', { name: 'Währung prüfen / bestätigen' }));
  fireEvent.change(await screen.findByLabelText('Ausführungswährung (Code)'), {
    target: { value: 'USD' },
  });
  timeline = [buy, sale, { ...buy, id: 'replacement', supersedes_id: buy.id }];
  changed();
  await screen.findByText(/Diese Buchung wurde bereits ersetzt/);
  expect(api.executionCurrencyHistory).toHaveBeenCalledOnce();
  expect(
    screen.queryByRole('button', { name: 'Währungsbestätigung speichern' }),
  ).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('tab', { name: 'Historie' }));
  expect(screen.getByRole('alertdialog')).toHaveTextContent('Ungespeicherte Änderungen');
  expect(api.confirmExecutionCurrency).not.toHaveBeenCalled();
});

it('blocks a date draft when its BUY currency source changes and retains the entered date', async () => {
  timeline = [{ ...sale, currency_resolution: unknown }];
  render(<ExecutionDatesPanel tradeId="trade" onChanged={onChanged} />);
  await open('Verkaufsdatum');
  changeDate('2026-08-23', 'Verkaufsdatum');
  confirm();
  timeline = [
    {
      ...sale,
      currency_resolution: {
        currency_code: 'EUR',
        source: 'PRIOR_BUYS',
        source_execution_ids: [buy.id],
        confirmation_ids: ['buy-confirmation'],
      },
    },
  ];
  changed();
  await screen.findByText(/Die Währungsquellen haben sich geändert/);
  expect(screen.getByLabelText('Verkaufsdatum korrigieren')).toHaveValue('2026-08-23');
  expect(screen.getByRole('button', { name: 'Datumsänderung speichern' })).toBeDisabled();
  fireEvent.click(screen.getByRole('button', { name: 'Neu gelesene Währungsherkunft geprüft' }));
  expect(screen.getByRole('checkbox', { name: /Ich bestätige/ })).not.toBeChecked();
  expect(screen.getByText('Währung: EUR · aus vorherigen Käufen übernommen')).toBeVisible();
  confirm();
  save();
  await screen.findByText(/Datum korrigiert/);
  expect(api.correctExecution.mock.calls[0][2]).not.toHaveProperty('currency_confirmation');
});

it('refreshes dependent SELL and additional BUY currencies after a separate BUY confirmation', async () => {
  const confirmation = currencyConfirmation(buy.id);
  const direct: ExecutionCurrencyResolution = {
    currency_code: 'EUR',
    source: 'USER_CONFIRMED',
    source_execution_ids: [buy.id],
    confirmation_ids: [confirmation.id],
  };
  const inherited: ExecutionCurrencyResolution = { ...direct, source: 'PRIOR_BUYS' };
  timeline = [buy, sale, { ...buy, id: 'additional-buy' }].map((entry) => ({
    ...entry,
    currency_resolution: unknown,
  }));
  api.confirmExecutionCurrency.mockImplementation(() => {
    timeline = timeline.map((entry) => ({
      ...entry,
      currency_confirmation: entry.id === buy.id ? confirmation : null,
      currency_resolution: entry.id === buy.id ? direct : inherited,
    }));
    api.executionCurrencyHistory.mockResolvedValue({
      current: confirmation,
      history: [confirmation],
      currency_resolution: direct,
    });
    return Promise.resolve(confirmation);
  });
  render(<ExecutionDatesPanel tradeId="trade" onChanged={onChanged} />);
  const row = within(await screen.findByRole('article', { name: 'Buchung buy' }));
  fireEvent.click(row.getByRole('button', { name: 'Währung prüfen / bestätigen' }));
  fireEvent.change(await screen.findByLabelText('Ausführungswährung (Code)'), {
    target: { value: 'EUR' },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Währungsbestätigung speichern' }));
  expect(
    await within(screen.getByRole('article', { name: 'Buchung sale' })).findByText(
      'EUR · aus vorherigen Käufen übernommen',
    ),
  ).toBeVisible();
  expect(
    within(screen.getByRole('article', { name: 'Buchung additional-buy' })).getByText(
      'EUR · aus vorherigen Käufen übernommen',
    ),
  ).toBeVisible();
  await waitFor(() =>
    expect(screen.getByRole('button', { name: 'Buchungseditor schließen' })).toBeEnabled(),
  );
  expect(api.confirmExecutionCurrency).toHaveBeenCalledOnce();
  expect(api.confirmExecutionCurrency.mock.calls[0][2].supersedes_confirmation_id).toBeNull();
  expect(api.correctExecution).not.toHaveBeenCalled();
  expect(onChanged).toHaveBeenCalledOnce();
});

it('preserves a rejected chronology draft without claiming success', async () => {
  api.correctExecution.mockRejectedValue(
    new MarketApiError(422, {
      code: 'INVALID',
      message: 'Verkauf liegt vor dem Kauf',
      details: [],
      timestamp: '2026-10-26T10:00:00Z',
    }),
  );
  render(<ExecutionDatesPanel tradeId="trade" onChanged={onChanged} />);
  await open('Verkaufsdatum');
  changeDate('2026-08-16', 'Verkaufsdatum');
  confirm();
  save();
  await screen.findByText(/Korrektur nicht bestätigt: Verkauf liegt vor dem Kauf/);
  expect(screen.getByLabelText('Verkaufsdatum korrigieren')).toHaveValue('2026-08-16');
  expect(onChanged).not.toHaveBeenCalled();
});

it('locks double submits and navigation synchronously while the correction is pending', async () => {
  const pending = deferred<SaleResponse>();
  api.correctExecution.mockReturnValue(pending.promise);
  const blocked = vi.fn();
  render(
    <ExecutionDatesPanel tradeId="trade" onChanged={onChanged} onWriteBlockedChange={blocked} />,
  );
  const form = await open();
  changeDate();
  confirm();
  fireEvent.submit(form);
  fireEvent.submit(form);
  expect(api.correctExecution).toHaveBeenCalledOnce();
  expect(blocked).toHaveBeenLastCalledWith(true);
  fireEvent.click(screen.getByRole('tab', { name: 'Historie' }));
  expect(screen.getByRole('alertdialog')).toHaveTextContent('Speicherung läuft');
  expect(
    screen.queryByRole('button', { name: 'Eingaben verwerfen und wechseln' }),
  ).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Hier bleiben' }));
  await act(() => {
    pending.resolve(corrected('trade', buy.id, api.correctExecution.mock.calls[0][2]));
    return pending.promise;
  });
  await screen.findByText(/Datum korrigiert/);
  expect(blocked).toHaveBeenLastCalledWith(false);
});

it('reads after uncertain transport and requires a deliberate check before another write to the same target', async () => {
  api.correctExecution.mockRejectedValueOnce(new Error('Verbindung unterbrochen'));
  render(<ExecutionDatesPanel tradeId="trade" onChanged={onChanged} />);
  await open();
  changeDate();
  confirm();
  save();
  await screen.findByText(/Ausgang des Korrekturauftrags ist unklar/);
  await waitFor(() =>
    expect(screen.getByRole('button', { name: 'Buchungsstand prüfen' })).toBeEnabled(),
  );
  expect(api.timeline).toHaveBeenCalledTimes(2);
  expect(onChanged).toHaveBeenCalledOnce();
  expect(screen.getByRole('checkbox', { name: /Ich bestätige/ })).toBeDisabled();
  fireEvent.submit(screen.getByRole('form'));
  expect(api.correctExecution).toHaveBeenCalledOnce();
  fireEvent.click(screen.getByRole('button', { name: 'Buchungsstand prüfen' }));
  await screen.findByText(/Buchungsstand neu gelesen/);
  expect(screen.getByLabelText('Kaufdatum korrigieren')).toHaveValue('2026-08-16');
  expect(screen.getByRole('checkbox', { name: /Ich bestätige/ })).not.toBeChecked();
  confirm();
  save();
  await screen.findByText(/Datum korrigiert/);
  expect(api.correctExecution.mock.calls.map((call) => call[1])).toEqual([buy.id, buy.id]);
  expect(api.correctExecution.mock.calls[0][2]).not.toHaveProperty('request_id');
});

it('never retries or switches targets when an uncertain POST actually created a replacement', async () => {
  api.correctExecution.mockImplementationOnce((tradeId, id, payload) => {
    corrected(tradeId, id, payload);
    return Promise.reject(new Error('Response lost'));
  });
  render(<ExecutionDatesPanel tradeId="trade" onChanged={onChanged} />);
  await open();
  changeDate();
  confirm();
  save();
  await screen.findByText(/Diese Buchung wurde bereits ersetzt/);
  await waitFor(() =>
    expect(screen.getByRole('button', { name: 'Buchungsstand prüfen' })).toBeEnabled(),
  );
  fireEvent.click(screen.getByRole('button', { name: 'Buchungsstand prüfen' }));
  await screen.findByText(/Buchungsstand neu gelesen/);
  expect(screen.getByRole('button', { name: 'Datumsänderung speichern' })).toBeDisabled();
  expect(api.correctExecution).toHaveBeenCalledOnce();
  expect(screen.queryByText(/Datum korrigiert/)).not.toBeInTheDocument();
});

it('separates confirmed write from failed projection readback and recovers without another POST', async () => {
  onChanged.mockRejectedValueOnce(new Error('Position offline'));
  render(<ExecutionDatesPanel tradeId="trade" onChanged={onChanged} />);
  await open();
  changeDate();
  confirm();
  save();
  await screen.findByText(/Datum gespeichert, Ansicht noch nicht aktualisiert/);
  expect(screen.queryByRole('form')).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Kaufdatum korrigieren' })).toBeDisabled();
  fireEvent.click(screen.getByRole('button', { name: 'Buchungsstand prüfen' }));
  await screen.findByText(/Gespeicherte Korrektur und aktueller Positionsstand/);
  expect(screen.getByRole('button', { name: 'Kaufdatum korrigieren' })).toBeEnabled();
  expect(api.correctExecution).toHaveBeenCalledOnce();
});

it('checks the timeline supersession link rather than assuming a response-only field', async () => {
  api.correctExecution.mockResolvedValue({
    execution: { id: 'unlinked', trade_id: 'trade' },
  } as SaleResponse);
  render(<ExecutionDatesPanel tradeId="trade" onChanged={onChanged} />);
  await open();
  changeDate();
  confirm();
  save();
  await screen.findByText(/Verknüpfung zur ursprünglichen Buchung/);
  expect(screen.queryByText(/Datum korrigiert/)).not.toBeInTheDocument();
  expect(screen.queryByRole('form')).not.toBeInTheDocument();
  timeline = [buy, sale, { ...buy, id: 'unlinked', supersedes_id: buy.id }];
  fireEvent.click(screen.getByRole('button', { name: 'Buchungsstand prüfen' }));
  await screen.findByText(/Gespeicherte Korrektur/);
  expect(api.correctExecution).toHaveBeenCalledOnce();
});

it('keeps recovery locked until both timeline and projection reads finish, including repeated reload clicks', async () => {
  onChanged.mockRejectedValueOnce(new Error('Position offline'));
  render(<ExecutionDatesPanel tradeId="trade" onChanged={onChanged} />);
  await open();
  changeDate();
  confirm();
  save();
  await screen.findByText(/Datum gespeichert, Ansicht noch nicht aktualisiert/);
  const projection = deferred<void>();
  onChanged.mockReturnValueOnce(projection.promise);
  const review = screen.getByRole('button', { name: 'Buchungsstand prüfen' });
  fireEvent.click(review);
  await waitFor(() => expect(api.timeline).toHaveBeenCalledTimes(3));
  expect(review).toBeDisabled();
  fireEvent.click(review);
  expect(onChanged).toHaveBeenCalledTimes(2);
  expect(screen.getByRole('button', { name: 'Kaufdatum korrigieren' })).toBeDisabled();
  await act(() => {
    projection.reject(new Error('Still offline'));
    return projection.promise.catch(() => undefined);
  });
  await screen.findByText(/Buchungsstand noch nicht vollständig geprüft: Still offline/);
  expect(review).toBeEnabled();
  expect(screen.getByRole('button', { name: 'Kaufdatum korrigieren' })).toBeDisabled();
  expect(api.correctExecution).toHaveBeenCalledOnce();
});

it('checks another page writer synchronously before submitting an already opened date editor', async () => {
  const writer = { busy: false };
  render(
    <TradePendingChangesProvider>
      <ExternalWriter state={writer} />
      <ExecutionDatesPanel tradeId="trade" onChanged={onChanged} />
    </TradePendingChangesProvider>,
  );
  const form = await open();
  changeDate();
  confirm();
  writer.busy = true;
  fireEvent.submit(form);
  expect(api.correctExecution).not.toHaveBeenCalled();
  writer.busy = false;
  fireEvent.submit(form);
  await screen.findByText(/Datum korrigiert/);
  expect(api.correctExecution).toHaveBeenCalledOnce();
});

it('preserves the date draft on same-trade reload and never shows a foreign timeline as its data', async () => {
  const { rerender } = render(<ExecutionDatesPanel tradeId="trade" onChanged={onChanged} />);
  await open();
  changeDate();
  confirm();
  rerender(<ExecutionDatesPanel tradeId="trade" onChanged={onChanged} reloadToken={1} />);
  await waitFor(() => expect(api.timeline).toHaveBeenCalledTimes(2));
  expect(screen.getByLabelText('Kaufdatum korrigieren')).toHaveValue('2026-08-16');
  expect(screen.getByRole('checkbox', { name: /Ich bestätige/ })).toBeChecked();
  timeline = [{ ...buy, trade_id: 'foreign', id: 'foreign-booking' }];
  changed();
  await screen.findByText(/Die gelesenen Buchungen gehören nicht zu diesem Trade/);
  expect(
    screen.queryByRole('article', { name: 'Buchung foreign-booking' }),
  ).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Datumsänderung speichern' })).toBeDisabled();
});

it('ignores late A responses after A→B→A including an obsolete successful write', async () => {
  const pending = deferred<SaleResponse>();
  api.correctExecution.mockReturnValueOnce(pending.promise);
  const { rerender } = render(<ExecutionDatesPanel tradeId="trade" onChanged={onChanged} />);
  await open();
  changeDate();
  confirm();
  save();
  timeline = [{ ...buy, trade_id: 'trade-b', id: 'b-buy' }];
  rerender(<ExecutionDatesPanel tradeId="trade-b" onChanged={onChanged} />);
  await screen.findByRole('article', { name: 'Buchung b-buy' });
  timeline = [buy];
  rerender(<ExecutionDatesPanel tradeId="trade" onChanged={onChanged} />);
  await open();
  changeDate('2026-08-15');
  await act(() => {
    pending.resolve({ execution: { id: 'old-result', trade_id: 'trade' } } as SaleResponse);
    return pending.promise;
  });
  expect(screen.getByLabelText('Kaufdatum korrigieren')).toHaveValue('2026-08-15');
  expect(screen.queryByText(/^Datum korrigiert|^Datum gespeichert/)).not.toBeInTheDocument();
  expect(onChanged).not.toHaveBeenCalled();
});

it('reports missing data, supports reload and never supplies placeholder executions', async () => {
  api.timeline.mockRejectedValueOnce(new Error('Nicht erreichbar'));
  render(<ExecutionDatesPanel tradeId="trade" onChanged={onChanged} />);
  await screen.findByRole('alert');
  expect(screen.queryByRole('button', { name: /korrigieren/ })).not.toBeInTheDocument();
  timeline = [];
  fireEvent.click(screen.getByRole('button', { name: 'Buchungsdaten neu laden' }));
  await screen.findByText(/Keine Kauf-\/Verkaufsbuchungen vorhanden/);
});

it('reports an incomplete stored date basis before opening an editor', async () => {
  timeline = [{ ...buy, execution_timezone: null }];
  render(<ExecutionDatesPanel tradeId="trade" onChanged={onChanged} />);
  fireEvent.click(await screen.findByRole('button', { name: 'Kaufdatum korrigieren' }));
  expect(screen.getByRole('status')).toHaveTextContent(
    'Die Zeitzone der gespeicherten Ausführung fehlt.',
  );
  expect(screen.queryByRole('form')).not.toBeInTheDocument();
  expect(api.correctExecution).not.toHaveBeenCalled();
});

it('supports keyboard tab navigation and focus without fetching another history', async () => {
  render(<ExecutionDatesPanel tradeId="trade" onChanged={onChanged} />);
  await screen.findByRole('article', { name: 'Buchung buy' });
  const current = screen.getByRole('tab', { name: 'Aktuelle Buchungen' });
  current.focus();
  fireEvent.keyDown(current, { key: 'ArrowRight' });
  expect(screen.getByRole('tab', { name: 'Historie' })).toHaveFocus();
  expect(screen.getByRole('tabpanel', { name: 'Historie' })).toBeVisible();
  fireEvent.keyDown(screen.getByRole('tab', { name: 'Historie' }), { key: 'Home' });
  expect(current).toHaveFocus();
  expect(api.timeline).toHaveBeenCalledOnce();
});
