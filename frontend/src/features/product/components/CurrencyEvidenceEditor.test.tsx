import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { marketApiClient } from '../../market/services/client';
import { MarketApiError } from '../../market/services/http';
import type { TradingVenueResponse } from '../../market/types/api';
import { currencyEvidenceApi } from '../services/currencyEvidence';
import type { CurrencyEvidence, CurrencyEvidenceHistory } from '../types/currencyEvidence';
import { CurrencyEvidenceEditor } from './CurrencyEvidenceEditor';

vi.mock('../services/currencyEvidence', () => ({
  currencyEvidenceApi: { history: vi.fn(), record: vi.fn() },
}));
vi.mock('../../market/services/client', () => ({
  marketApiClient: { listTradingVenues: vi.fn() },
}));
const api = vi.mocked(currencyEvidenceApi);
const venue = {
  id: 'xetra',
  name: 'Xetra',
  mic: 'XETR',
  country_code: 'DE',
  timezone: 'Europe/Berlin',
  reference_version: 'test',
} satisfies TradingVenueResponse;
const frankfurt = { ...venue, id: 'frankfurt', name: 'Frankfurt', mic: 'XFRA' };
const source: CurrencyEvidence = {
  id: 'version-1',
  product_id: 'product',
  workspace_id: 'workspace',
  kind: 'HISTORICAL_LISTINGS',
  source_reference: 'Synthetic historical exchange source',
  recorded_at: '2026-10-28T12:00:00Z',
  recorded_by: 'actor',
  request_id: 'request-old',
  request_fingerprint: 'fingerprint',
  verification: 'USER_VERIFIED_SOURCE',
  supersedes_evidence_id: null,
  revoked: false,
  trade_id: null,
  execution_id: null,
  currency_code: null,
  trading_venue_id: null,
  valid_from: '2026-09-01T00:00:00+02:00',
  valid_to: '2026-11-01T00:00:00+01:00',
  listings: [{ trading_venue_id: 'xetra', currency_code: 'EUR' }],
  complete_listing_set: true,
};
function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((yes) => {
    resolve = yes;
  });
  return { resolve, promise };
}
function input(label: string, value: string) {
  fireEvent.change(screen.getByLabelText(label), { target: { value } });
}
async function load() {
  fireEvent.click(screen.getByRole('button', { name: 'Währungsquellen laden' }));
  await screen.findByRole('form', { name: 'Währungsquelle prüfen und speichern' });
}
function fillHistorical() {
  fireEvent.click(screen.getByRole('button', { name: 'Genaue Zeitpunkte mit Zeitzone verwenden' }));
  input('Quelle und Fundstelle', source.source_reference);
  input('Gültig ab, mit Zeitzone', source.valid_from!);
  input('Gültig bis ausschließlich, mit Zeitzone', source.valid_to!);
  input('Historischer Handelsplatz 1', 'xetra');
  input('Historische Währung 1', 'eur');
}
function attest() {
  fireEvent.click(screen.getByRole('checkbox', { name: /Ich habe die Originalquelle geprüft/ }));
}
beforeEach(() => {
  vi.resetAllMocks();
  sessionStorage.clear();
  vi.spyOn(window, 'confirm').mockReturnValue(true);
  api.history.mockResolvedValue({ history: [] });
  vi.mocked(marketApiClient.listTradingVenues).mockResolvedValue({ items: [venue, frankfurt] });
  api.record.mockImplementation((product, request) =>
    Promise.resolve({ ...source, ...request, product_id: product, id: 'version-new' }),
  );
});

it('loads on demand, never treats current listings as historical defaults, and saves one reviewed source for multiple venues', async () => {
  const pending = vi.fn();
  render(
    <CurrencyEvidenceEditor
      productId="product"
      venues={[venue, frankfurt]}
      onPendingChange={pending}
    />,
  );
  expect(api.history).not.toHaveBeenCalled();
  expect(api.record).not.toHaveBeenCalled();
  await load();
  expect(screen.getByLabelText('Historischer Handelsplatz 1')).toHaveValue('');
  expect(screen.getByLabelText('Historische Währung 1')).toHaveValue('');
  expect(screen.getByLabelText('Historisch gültig ab (einschließlich)')).toHaveValue('');
  expect(screen.getByRole('checkbox', { name: /alle relevanten Handelsplätze/ })).not.toBeChecked();
  fillHistorical();
  fireEvent.click(screen.getByRole('button', { name: 'Historischen Handelsplatz ergänzen' }));
  input('Historischer Handelsplatz 2', 'frankfurt');
  input('Historische Währung 2', 'EUR');
  expect(screen.getByRole('button', { name: 'Geprüfte Quellenversion speichern' })).toBeDisabled();
  fireEvent.click(screen.getByRole('checkbox', { name: /alle relevanten Handelsplätze/ }));
  attest();
  fireEvent.click(screen.getByRole('button', { name: 'Geprüfte Quellenversion speichern' }));
  await screen.findByText(/Quellenversion gespeichert/);
  expect(api.record).toHaveBeenCalledExactlyOnceWith(
    'product',
    expect.objectContaining({
      kind: 'HISTORICAL_LISTINGS',
      source_reference: source.source_reference,
      valid_from: source.valid_from,
      valid_to: source.valid_to,
      complete_listing_set: true,
      listings: [
        { trading_venue_id: 'xetra', currency_code: 'EUR' },
        { trading_venue_id: 'frankfurt', currency_code: 'EUR' },
      ],
      trade_id: null,
      execution_id: null,
      currency_code: null,
      supersedes_evidence_id: null,
      request_id: expect.any(String),
      confirmation: 'CONFIRM_SOURCE_REVIEW',
    }),
    expect.any(AbortSignal),
  );
  expect(screen.getByText(/aktuelle Quellenversion/)).toBeVisible();
  expect(pending).toHaveBeenLastCalledWith({ dirty: false, busy: false, writeBlocked: false });
});

it('requires explicit timezone and unique venues, without silently completing missing historical coverage', async () => {
  render(<CurrencyEvidenceEditor productId="product" />);
  await load();
  fillHistorical();
  input('Gültig ab, mit Zeitzone', '2026-09-01T00:00:00');
  attest();
  fireEvent.submit(screen.getByRole('form'));
  expect(await screen.findByRole('alert')).toHaveTextContent('ausdrücklicher Zeitzone');
  expect(api.record).not.toHaveBeenCalled();
  input('Gültig ab, mit Zeitzone', source.valid_from!);
  expect(screen.getByRole('checkbox', { name: /Originalquelle/ })).not.toBeChecked();
  fireEvent.click(screen.getByRole('button', { name: 'Historischen Handelsplatz ergänzen' }));
  input('Historischer Handelsplatz 2', 'xetra');
  attest();
  fireEvent.submit(screen.getByRole('form'));
  expect(await screen.findByRole('alert')).toHaveTextContent('nur einmal');
  expect(api.record).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button', { name: 'Handelsplatz 2 entfernen' }));
  input('Historische Währung 1', '');
  attest();
  fireEvent.submit(screen.getByRole('form'));
  await waitFor(() => expect(api.record).toHaveBeenCalledOnce());
  expect(api.record.mock.calls[0][1]).toMatchObject({
    complete_listing_set: false,
    listings: [{ trading_venue_id: 'xetra', currency_code: null }],
  });
});

it('pins correction and revocation to the exact source version while preserving the readable history', async () => {
  api.history.mockResolvedValue({ history: [source] });
  render(<CurrencyEvidenceEditor productId="product" />);
  await load();
  fireEvent.click(screen.getByRole('button', { name: 'Quelle korrigieren' }));
  expect(screen.getByLabelText('Historische Währung 1')).toHaveValue('EUR');
  input('Historische Währung 1', 'CHF');
  attest();
  fireEvent.submit(screen.getByRole('form'));
  await screen.findByText(/Quellenversion gespeichert/);
  expect(api.record.mock.calls[0][1]).toMatchObject({
    supersedes_evidence_id: source.id,
    listings: [{ trading_venue_id: 'xetra', currency_code: 'CHF' }],
    revoked: false,
  });
  expect(screen.getByText(`${source.source_reference} · ersetzt`)).toBeVisible();
  fireEvent.click(screen.getByRole('button', { name: 'Widerruf vorbereiten' }));
  expect(api.record).toHaveBeenCalledOnce();
  expect(screen.getByLabelText('Quelle und Fundstelle')).toBeDisabled();
  fireEvent.click(screen.getByRole('checkbox', { name: /widerrufe diese Zuordnung/ }));
  api.record.mockImplementationOnce((product, request) =>
    Promise.resolve({ ...source, ...request, product_id: product, id: 'revocation' }),
  );
  fireEvent.click(screen.getByRole('button', { name: 'Quellenwiderruf speichern' }));
  await screen.findByText(/Quelle widerrufen/);
  expect(api.record.mock.calls[1][1]).toMatchObject({
    supersedes_evidence_id: 'version-new',
    revoked: true,
    listings: [{ trading_venue_id: 'xetra', currency_code: 'CHF' }],
  });
  expect(screen.getByText(`${source.source_reference} · widerrufen`)).toBeVisible();
  expect(screen.queryByRole('button', { name: 'Quelle korrigieren' })).not.toBeInTheDocument();
});

it('binds a document to the selected execution and accepts a known venue without inventing its currency', async () => {
  const other = {
    ...source,
    id: 'other-execution',
    kind: 'EXECUTION_DOCUMENT' as const,
    trade_id: 'other',
    execution_id: 'other-execution',
  };
  api.history.mockResolvedValue({ history: [source, other] });
  render(
    <CurrencyEvidenceEditor
      productId="product"
      execution={{ tradeId: 'trade', executionId: 'sell' }}
    />,
  );
  await load();
  expect(screen.queryByText('Synthetic historical exchange source')).not.toBeInTheDocument();
  expect(screen.queryByLabelText('Gültig ab, mit Zeitzone')).not.toBeInTheDocument();
  input('Quelle und Fundstelle', 'Abrechnung Nr. 42, Ausführung');
  input('Handelsplatz laut Ausführungsbeleg (optional)', 'xetra');
  attest();
  fireEvent.submit(screen.getByRole('form'));
  await screen.findByText(/Quellenversion gespeichert/);
  expect(api.record.mock.calls[0][1]).toMatchObject({
    kind: 'EXECUTION_DOCUMENT',
    trade_id: 'trade',
    execution_id: 'sell',
    currency_code: null,
    trading_venue_id: 'xetra',
    valid_from: null,
    valid_to: null,
    listings: [],
    complete_listing_set: false,
  });
  expect(screen.getByText(/Ausführungswährung unbekannt/)).toBeVisible();
});

it('keeps a lost-response retry immutable and sends only one request for double submission', async () => {
  const outstanding = deferred<CurrencyEvidence>();
  api.record.mockReturnValueOnce(outstanding.promise);
  render(<CurrencyEvidenceEditor productId="product" />);
  await load();
  fillHistorical();
  attest();
  fireEvent.submit(screen.getByRole('form'));
  fireEvent.submit(screen.getByRole('form'));
  expect(api.record).toHaveBeenCalledOnce();
  const request = api.record.mock.calls[0][1];
  await act(async () => {
    outstanding.resolve({ ...source, ...request, product_id: 'wrong-product' });
    await outstanding.promise;
  });
  expect(await screen.findByRole('alert')).toHaveTextContent('Speichererfolg unklar');
  expect(screen.getByLabelText('Historische Währung 1')).toBeDisabled();
  fireEvent.click(screen.getByRole('button', { name: 'Denselben Quellenauftrag erneut senden' }));
  await screen.findByText(/Quellenversion gespeichert/);
  expect(api.record.mock.calls[1][1]).toEqual(request);
});

it('requires a deliberate reload after a competing correction before accepting a new edit', async () => {
  api.history.mockResolvedValue({ history: [source] });
  api.record.mockRejectedValueOnce(
    new MarketApiError(409, {
      code: 'CURRENCY_EVIDENCE_CONFLICT',
      message: 'Concurrent correction',
      details: [],
      timestamp: source.recorded_at,
    }),
  );
  render(<CurrencyEvidenceEditor productId="product" />);
  await load();
  fireEvent.click(screen.getByRole('button', { name: 'Quelle korrigieren' }));
  input('Historische Währung 1', 'USD');
  attest();
  fireEvent.submit(screen.getByRole('form'));
  expect(await screen.findByRole('alert')).toHaveTextContent('inzwischen geändert');
  expect(screen.getByRole('button', { name: 'Geprüfte Quellenversion speichern' })).toBeDisabled();
  expect(screen.getByLabelText('Historische Währung 1')).toHaveValue('USD');
  await load();
  await waitFor(() => expect(screen.getByLabelText('Historische Währung 1')).toHaveValue(''));
  expect(screen.getByRole('checkbox', { name: /Originalquelle/ })).not.toBeChecked();
  expect(api.record).toHaveBeenCalledOnce();
});

it('ignores late reads after a product switch and rejects mismatched product histories', async () => {
  const first = deferred<CurrencyEvidenceHistory>();
  api.history.mockReturnValueOnce(first.promise).mockResolvedValue({ history: [source] });
  const { rerender } = render(<CurrencyEvidenceEditor productId="product" />);
  fireEvent.click(screen.getByRole('button', { name: 'Währungsquellen laden' }));
  const signal = api.history.mock.calls[0][1]!;
  rerender(<CurrencyEvidenceEditor productId="second-product" />);
  expect(signal.aborted).toBe(true);
  await act(async () => {
    first.resolve({ history: [source] });
    await first.promise;
  });
  expect(screen.queryByRole('form')).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Währungsquellen laden' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('anderen Produkt');
  expect(screen.queryByRole('form')).not.toBeInTheDocument();
});

it('does not leak a completed write into a newly selected execution', async () => {
  const outstanding = deferred<CurrencyEvidence>();
  const changed = vi.fn().mockResolvedValue(undefined);
  api.record.mockReturnValueOnce(outstanding.promise);
  const { rerender } = render(
    <CurrencyEvidenceEditor
      productId="product"
      execution={{ tradeId: 'trade', executionId: 'buy' }}
      onChanged={changed}
    />,
  );
  await load();
  input('Quelle und Fundstelle', 'Buy document');
  input('Währung laut Ausführungsbeleg', 'EUR');
  attest();
  fireEvent.submit(screen.getByRole('form'));
  const request = api.record.mock.calls[0][1];
  rerender(
    <CurrencyEvidenceEditor
      productId="product"
      execution={{ tradeId: 'trade', executionId: 'sell' }}
      onChanged={changed}
    />,
  );
  await act(async () => {
    outstanding.resolve({ ...source, ...request });
    await outstanding.promise;
  });
  expect(changed).not.toHaveBeenCalled();
  expect(screen.queryByText(/Quellenversion gespeichert/)).not.toBeInTheDocument();
  expect(screen.queryByRole('form')).not.toBeInTheDocument();
});

it('retains confirmed save success when owner refresh fails and refreshes before unblocking further writes', async () => {
  const changed = vi
    .fn()
    .mockRejectedValueOnce(new Error('owner unavailable'))
    .mockResolvedValue(undefined);
  render(<CurrencyEvidenceEditor productId="product" onChanged={changed} />);
  await load();
  fillHistorical();
  attest();
  fireEvent.submit(screen.getByRole('form'));
  expect(await screen.findByRole('alert')).toHaveTextContent('Quelle gespeichert');
  expect(screen.getByText(/Quellenversion gespeichert/)).toBeVisible();
  expect(screen.getByLabelText('Quelle und Fundstelle')).toBeDisabled();
  api.history.mockResolvedValue({
    history: [{ ...source, ...api.record.mock.calls[0][1], id: 'version-new' }],
  });
  fireEvent.click(screen.getByRole('button', { name: 'Währungsquellen laden' }));
  await waitFor(() => expect(changed).toHaveBeenCalledTimes(2));
  await waitFor(() => expect(screen.getByLabelText('Quelle und Fundstelle')).toBeEnabled());
  expect(api.record).toHaveBeenCalledOnce();
  const recorded = screen.getByLabelText('Gespeicherte Währungsquellen');
  expect(within(recorded).getByText(/aktuelle Quellenversion/)).toBeVisible();
});

it('ends an uncertain retry after a definitive conflict and requires source and owner readback', async () => {
  const changed = vi.fn().mockResolvedValue(undefined);
  api.record.mockRejectedValueOnce(new Error('response lost')).mockRejectedValueOnce(
    new MarketApiError(409, {
      code: 'CURRENCY_EVIDENCE_CONFLICT',
      message: 'source changed',
      details: [],
      timestamp: source.recorded_at,
    }),
  );
  render(<CurrencyEvidenceEditor productId="product" onChanged={changed} />);
  await load();
  fillHistorical();
  attest();
  fireEvent.submit(screen.getByRole('form'));
  await screen.findByText(/Speichererfolg unklar/);
  fireEvent.click(screen.getByRole('button', { name: 'Denselben Quellenauftrag erneut senden' }));
  await screen.findByText(/inzwischen geändert/);
  expect(
    screen.queryByRole('button', { name: 'Denselben Quellenauftrag erneut senden' }),
  ).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Geprüfte Quellenversion speichern' })).toBeDisabled();
  fireEvent.click(screen.getByRole('button', { name: 'Währungsquellen laden' }));
  await waitFor(() => expect(changed).toHaveBeenCalledOnce());
  await waitFor(() => expect(screen.getByLabelText('Quelle und Fundstelle')).toBeEnabled());
  expect(api.record).toHaveBeenCalledTimes(2);
});

it('checks a shared in-flight writer synchronously before a document write', async () => {
  let blocked = false;
  render(
    <CurrencyEvidenceEditor
      productId="product"
      execution={{ tradeId: 'trade', executionId: 'buy' }}
      isWriteBlocked={() => blocked}
    />,
  );
  await load();
  input('Quelle und Fundstelle', 'Ausführungsbeleg');
  input('Währung laut Ausführungsbeleg', 'EUR');
  attest();
  blocked = true;
  fireEvent.submit(screen.getByRole('form'));
  expect(api.record).not.toHaveBeenCalled();
  blocked = false;
  fireEvent.submit(screen.getByRole('form'));
  await screen.findByText(/Quellenversion gespeichert/);
  expect(api.record).toHaveBeenCalledOnce();
});

it('does not treat an empty readback after an uncertain POST as proof that the original request failed', async () => {
  const pending = vi.fn();
  api.record.mockRejectedValueOnce(new Error('response lost while server may still commit'));
  render(<CurrencyEvidenceEditor productId="product" onPendingChange={pending} />);
  await load();
  fillHistorical();
  attest();
  fireEvent.submit(screen.getByRole('form'));
  await screen.findByText(/Speichererfolg unklar/);
  const originalRequest = api.record.mock.calls[0][1];
  api.history.mockResolvedValue({ history: [] });
  fireEvent.click(screen.getByRole('button', { name: 'Währungsquellen laden' }));
  await screen.findByText(/fehlender Eintrag beim Lesen beweist nicht/);
  expect(window.confirm).not.toHaveBeenCalled();
  expect(screen.getByLabelText('Quelle und Fundstelle')).toHaveValue(source.source_reference);
  expect(screen.getByLabelText('Historische Währung 1')).toHaveValue('EUR');
  expect(screen.getByLabelText('Historische Währung 1')).toBeDisabled();
  expect(pending).toHaveBeenLastCalledWith({ dirty: true, busy: false, writeBlocked: true });
  fireEvent.change(screen.getByLabelText('Historische Währung 1'), { target: { value: 'USD' } });
  expect(screen.getByLabelText('Historische Währung 1')).toHaveValue('EUR');
  fireEvent.click(screen.getByRole('button', { name: 'Denselben Quellenauftrag erneut senden' }));
  await screen.findByText(/Quellenversion gespeichert/);
  expect(api.record).toHaveBeenCalledTimes(2);
  expect(api.record.mock.calls[1][1]).toEqual(originalRequest);
  expect(pending).toHaveBeenLastCalledWith({ dirty: false, busy: false, writeBlocked: false });
});

it('resolves an uncertain write only when the exact request receipt is present in source history', async () => {
  const changed = vi.fn().mockResolvedValue(undefined);
  api.record.mockRejectedValueOnce(new Error('response lost'));
  render(<CurrencyEvidenceEditor productId="product" onChanged={changed} />);
  await load();
  fillHistorical();
  attest();
  fireEvent.submit(screen.getByRole('form'));
  await screen.findByText(/Speichererfolg unklar/);
  const originalRequest = api.record.mock.calls[0][1];
  api.history.mockResolvedValue({
    history: [{ ...source, ...originalRequest, id: 'committed-source' }],
  });
  fireEvent.click(screen.getByRole('button', { name: 'Währungsquellen laden' }));
  await screen.findByText(/Speicherung ist durch die gelesene Quellenversion bestätigt/);
  await waitFor(() => expect(screen.getByLabelText('Quelle und Fundstelle')).toBeEnabled());
  expect(changed).toHaveBeenCalledOnce();
  expect(api.record).toHaveBeenCalledOnce();
  expect(
    screen.queryByRole('button', { name: 'Denselben Quellenauftrag erneut senden' }),
  ).not.toBeInTheDocument();
});

it('offers inclusive native dates with a visible browser zone and submits their real local midnight boundaries', async () => {
  render(<CurrencyEvidenceEditor productId="product" />);
  await load();
  expect(screen.getByText(/Ganze Kalendertage in Ihrer Browserzeitzone/)).toHaveTextContent(
    Intl.DateTimeFormat().resolvedOptions().timeZone,
  );
  expect(screen.getByLabelText('Historisch gültig ab (einschließlich)')).toHaveAttribute(
    'type',
    'date',
  );
  input('Quelle und Fundstelle', 'Historical full-day source');
  input('Historisch gültig ab (einschließlich)', '2026-10-01');
  input('Historisch gültig bis (einschließlich)', '2026-10-28');
  input('Historischer Handelsplatz 1', 'xetra');
  input('Historische Währung 1', 'EUR');
  attest();
  fireEvent.submit(screen.getByRole('form'));
  await screen.findByText(/Quellenversion gespeichert/);
  const request = api.record.mock.calls[0][1];
  expect(request.valid_from).toBe(new Date(2026, 9, 1, 0, 0, 0, 0).toISOString());
  expect(request.valid_to).toBe(new Date(2026, 9, 29, 0, 0, 0, 0).toISOString());
});

it('keeps an existing intraday source exact when correcting its currency', async () => {
  const intraday = {
    ...source,
    valid_from: '2026-10-01T09:43:15.123+02:00',
    valid_to: '2026-10-28T17:08:03.456+01:00',
  };
  api.history.mockResolvedValue({ history: [intraday] });
  render(<CurrencyEvidenceEditor productId="product" />);
  await load();
  fireEvent.click(screen.getByRole('button', { name: 'Quelle korrigieren' }));
  expect(screen.getByLabelText('Gültig ab, mit Zeitzone')).toHaveValue(intraday.valid_from);
  expect(screen.getByLabelText('Gültig bis ausschließlich, mit Zeitzone')).toHaveValue(
    intraday.valid_to,
  );
  expect(screen.queryByLabelText('Historisch gültig ab (einschließlich)')).not.toBeInTheDocument();
  input('Historische Währung 1', 'CHF');
  attest();
  fireEvent.submit(screen.getByRole('form'));
  await screen.findByText(/Quellenversion gespeichert/);
  expect(api.record.mock.calls[0][1]).toMatchObject({
    valid_from: intraday.valid_from,
    valid_to: intraday.valid_to,
    supersedes_evidence_id: intraday.id,
  });
});
