import { act, fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { dataEvidenceApi } from '../services/dataEvidence';
import type { QuoteHistoryReport } from '../types/dataEvidence';
import { WarrantQuoteHistory } from './WarrantQuoteHistory';
vi.mock('../services/dataEvidence', () => ({ dataEvidenceApi: { history: vi.fn() } }));
const empty: QuoteHistoryReport = {
  warrant_id: 'w',
  window_start: '2026-10-01T12:00:00Z',
  window_end: '2026-10-08T12:00:00Z',
  collection_started_at: null,
  item_limit: 50,
  segments: [],
  items: [],
};
function open() {
  render(<WarrantQuoteHistory warrantId="w" />);
  fireEvent.click(screen.getByText('Kursdaten-Verfügbarkeit und Erfassungsprotokoll'));
}
function load() {
  fireEvent.click(screen.getByRole('button', { name: 'Gespeichertes Protokoll laden' }));
}
describe('stored quote evidence', () => {
  beforeEach(() => vi.clearAllMocks());
  it('does not fetch on opening and distinguishes missing coverage from low risk', async () => {
    vi.mocked(dataEvidenceApi.history).mockResolvedValue(empty);
    open();
    expect(dataEvidenceApi.history).not.toHaveBeenCalled();
    load();
    expect(await screen.findByText(/Daraus folgt keine Entwarnung/)).toBeVisible();
    expect(screen.getByText(/Nicht erfasste Intervalle sind unbekannt/)).toBeVisible();
    expect(screen.getByText(/Noch keine IV-Historie/)).toBeVisible();
    expect(screen.queryByText('0 %')).not.toBeInTheDocument();
    expect(dataEvidenceApi.history).toHaveBeenCalledWith('w', 7, expect.any(AbortSignal));
  });
  it('separates clocks, references, failures and source segments without filling absent prices', async () => {
    vi.mocked(dataEvidenceApi.history).mockResolvedValue({
      ...empty,
      collection_started_at: '2026-10-07T10:00:00Z',
      segments: [
        {
          provider: 'FRANKFURT',
          identity_key: 'route-a',
          isin: 'DE000VH2LU21',
          sampled_slots: 2,
          distinct_quote_evidence: 1,
          observed_utc_days: 1,
          first_capture_at: '2026-10-07T10:00:00Z',
          last_capture_at: '2026-10-07T10:05:00Z',
          statuses: { TIMESTAMP_UNKNOWN: 1, REQUEST_FAILED: 1, TWO_SIDED_WITHIN_AGE_LIMIT: 0 },
        },
      ],
      items: [
        {
          id: 'a',
          provider: 'FRANKFURT',
          identity_key: 'route-a',
          isin: 'DE000VH2LU21',
          captured_at: '2026-10-07T10:00:00Z',
          slot_at: '2026-10-07T10:00:00Z',
          status: 'TIMESTAMP_UNKNOWN',
          reason: null,
          retrieved_at: '2026-10-07T09:59:00Z',
          cache_status: 'HIT',
          quote: {
            bid: null,
            ask: null,
            reference_price: '.23',
            reference_price_type: 'LAST_TRADE',
            currency: 'EUR',
            observed_at: null,
            source_mode: 'OFFICIAL_WEBSITE_LAST_TRADE',
          },
        },
        {
          id: 'b',
          provider: 'FRANKFURT',
          identity_key: 'route-b',
          isin: 'DE000VH2LU21',
          captured_at: '2026-10-07T10:05:00Z',
          slot_at: '2026-10-07T10:05:00Z',
          status: 'REQUEST_FAILED',
          reason: 'FRANKFURT_REQUEST_THROTTLED',
          retrieved_at: null,
          cache_status: null,
          quote: null,
        },
      ],
    });
    open();
    load();
    await screen.findByText(/2 erfasste Intervalle/);
    fireEvent.click(screen.getByText('Letzte 50 Beobachtungen mit Originalzeiten'));
    expect(screen.getAllByText(/Originalkurszeit: unbekannt/)).toHaveLength(2);
    expect(screen.getByText(/Abrufzeit: 2026-10-07T09:59:00Z/)).toHaveTextContent(
      'Erfasst: 2026-10-07T10:00:00Z',
    );
    expect(screen.getByText(/Referenz: .23/)).toBeVisible();
    expect(screen.getAllByText(/Geld: nicht vorhanden/)).toHaveLength(2);
    expect(screen.getByText(/Diagnose: FRANKFURT_REQUEST_THROTTLED/)).toBeVisible();
    expect(screen.getByText(/Quellsegment route-b/)).toBeVisible();
  });
  it('discards an obsolete in-flight window and shows request failures', async () => {
    let resolve!: (value: QuoteHistoryReport) => void;
    vi.mocked(dataEvidenceApi.history).mockImplementationOnce(
      () =>
        new Promise((r) => {
          resolve = r;
        }),
    );
    open();
    load();
    const signal = vi.mocked(dataEvidenceApi.history).mock.calls[0][2]!;
    fireEvent.change(screen.getByLabelText('Beobachtungsfenster'), { target: { value: '31' } });
    expect(signal.aborted).toBe(true);
    await act(() => {
      resolve(empty);
      return Promise.resolve();
    });
    expect(screen.queryByText(/Daraus folgt keine Entwarnung/)).not.toBeInTheDocument();
    vi.mocked(dataEvidenceApi.history).mockRejectedValueOnce(new Error('offline'));
    load();
    expect(await screen.findByRole('alert')).toHaveTextContent('kein neues Ergebnis');
    expect(dataEvidenceApi.history).toHaveBeenLastCalledWith('w', 31, expect.any(AbortSignal));
  });
  it('aborts when leaving a product', () => {
    vi.mocked(dataEvidenceApi.history).mockImplementation(() => new Promise(() => {}));
    const { unmount } = render(<WarrantQuoteHistory warrantId="w" />);
    fireEvent.click(screen.getByText('Kursdaten-Verfügbarkeit und Erfassungsprotokoll'));
    load();
    const signal = vi.mocked(dataEvidenceApi.history).mock.calls[0][2]!;
    unmount();
    expect(signal.aborted).toBe(true);
  });
});
