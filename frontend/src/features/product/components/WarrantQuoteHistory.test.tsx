import { act, fireEvent, render, screen, within } from '@testing-library/react';
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
const recorded: QuoteHistoryReport = {
  ...empty,
  collection_started_at: '2026-09-01T10:00:00Z',
  sampling_policy: 'FIRST_CAPTURE_PER_ROUTE_5_MIN_UTC_V1',
  time_coverage_percent: null,
  iv_history_available: false,
  underlying_synchronization_available: false,
  execution_usable: false,
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
      statuses: { TIMESTAMP_UNKNOWN: 2, REQUEST_FAILED: 0, TWO_SIDED_WITHIN_AGE_LIMIT: 0 },
    },
    {
      provider: 'FRANKFURT',
      identity_key: 'route-b',
      isin: 'DE000VH2LU21',
      sampled_slots: 1,
      distinct_quote_evidence: 0,
      observed_utc_days: 1,
      first_capture_at: '2026-10-07T10:06:00Z',
      last_capture_at: '2026-10-07T10:06:00Z',
      statuses: { REQUEST_FAILED: 1, TWO_SIDED_WITHIN_AGE_LIMIT: 0 },
    },
  ],
  items: [
    {
      id: 'sample-a',
      provider: 'FRANKFURT',
      identity_key: 'route-a',
      isin: 'DE000VH2LU21',
      captured_at: '2026-10-07T10:01:00Z',
      slot_at: '2026-10-07T10:00:00Z',
      status: 'TIMESTAMP_UNKNOWN',
      reason: null,
      retrieved_at: '2026-10-07T09:59:00Z',
      cache_status: 'HIT',
      quote_fingerprint: 'historical-quote-fingerprint-a',
      quote: {
        bid: null,
        ask: null,
        reference_price: '.23',
        reference_price_type: 'LAST_TRADE',
        currency: 'EUR',
        observed_at: null,
        source_mode: 'OFFICIAL_WEBSITE_LAST_TRADE',
        warrant_listing_id: 'historical-listing-a',
        provider_symbol: 'DE000VH2LU21',
        provider_exchange_code: 'FRA',
        venue_mic: 'XFRA',
        quote_time_text: '07.10.2026 11:30',
        quote_time_basis: 'LOCAL_DATETIME_TIMEZONE_UNKNOWN',
      },
    },
    {
      id: 'sample-b',
      provider: 'FRANKFURT',
      identity_key: 'route-b',
      isin: 'DE000VH2LU21',
      captured_at: '2026-10-07T10:06:00Z',
      slot_at: '2026-10-07T10:05:00Z',
      status: 'REQUEST_FAILED',
      reason: 'FRANKFURT_REQUEST_THROTTLED',
      retrieved_at: null,
      cache_status: null,
      quote: null,
    },
  ],
};

function open() {
  render(<WarrantQuoteHistory warrantId="w" />);
  fireEvent.click(screen.getByText('Kursdaten-Verfügbarkeit und Erfassungsprotokoll'));
}
function load() {
  fireEvent.click(screen.getByRole('button', { name: 'Gespeichertes Protokoll laden' }));
}
function evidenceValue(container: HTMLElement, label: string) {
  return within(container).getByText(label, { selector: 'dt' }).nextElementSibling;
}
function observations() {
  fireEvent.click(screen.getByText(/Erfassungsbelege mit Originalzeiten/));
  return within(
    screen.getByRole('list', { name: 'Einzelne gespeicherte Erfassungsbelege' }),
  ).getAllByRole('listitem');
}

describe('stored quote evidence', () => {
  beforeEach(() => vi.clearAllMocks());
  it('does not fetch on opening and distinguishes missing coverage from low risk', async () => {
    vi.mocked(dataEvidenceApi.history).mockResolvedValue({
      ...empty,
      sampling_policy: recorded.sampling_policy,
      time_coverage_percent: null,
      iv_history_available: false,
      underlying_synchronization_available: false,
      execution_usable: false,
    });
    open();
    expect(dataEvidenceApi.history).not.toHaveBeenCalled();
    load();
    expect(await screen.findByText(/Daraus folgt keine Entwarnung/)).toBeVisible();
    expect(screen.getByText(/Nicht erfasste Intervalle sind unbekannt/)).toBeVisible();
    const report = screen.getByRole('region', { name: 'Gespeicherte Kursbeobachtungen' });
    expect(evidenceValue(report, 'IV-Historie verfügbar (Backendangabe)')).toHaveTextContent(
      'nein',
    );
    expect(evidenceValue(report, 'Zeitabdeckungsquote')).toHaveTextContent('nicht verfügbar');
    expect(screen.getByText(/einschließlich Fehlern. Ein späterer Erfolg/)).toBeVisible();
    expect(screen.queryByText('0 %')).not.toBeInTheDocument();
    expect(report).not.toHaveAttribute('aria-live');
    expect(screen.getByRole('status')).toHaveTextContent('Protokoll geladen.');
    expect(dataEvidenceApi.history).toHaveBeenCalledWith('w', 7, expect.any(AbortSignal));
  });
  it('separates clocks, references, failures and source segments without filling absent prices', async () => {
    vi.mocked(dataEvidenceApi.history).mockResolvedValue(recorded);
    open();
    load();
    await screen.findByText('Protokoll geladen.');
    const [reference, failure] = observations();
    expect(evidenceValue(reference, 'Originalkurszeit (UTC)')).toHaveTextContent('unbekannt');
    expect(evidenceValue(reference, 'Erfassungszeit (UTC)')).toHaveTextContent(
      '2026-10-07T10:01:00Z',
    );
    expect(evidenceValue(reference, 'Abrufzeit (UTC)')).toHaveTextContent('2026-10-07T09:59:00Z');
    expect(evidenceValue(reference, 'Erfassungsslot (UTC)')).toHaveTextContent(
      '2026-10-07T10:00:00Z',
    );
    expect(evidenceValue(reference, 'Originalzeittext der Quelle (unverändert)')).toHaveTextContent(
      '07.10.2026 11:30',
    );
    expect(evidenceValue(reference, 'Zeitbasis der Quelle')).toHaveTextContent(
      'LOCAL_DATETIME_TIMEZONE_UNKNOWN',
    );
    expect(evidenceValue(reference, 'Referenzkurs')).toHaveTextContent('.23');
    expect(evidenceValue(reference, 'Referenz-Preisart')).toHaveTextContent('LAST_TRADE');
    expect(evidenceValue(reference, 'Geldkurs (BID)')).toHaveTextContent('nicht vorhanden');
    expect(evidenceValue(reference, 'Briefkurs (ASK)')).toHaveTextContent('nicht vorhanden');
    expect(evidenceValue(reference, 'Währung der Preise')).toHaveTextContent('EUR');
    expect(evidenceValue(reference, 'Handelsplatz (MIC)')).toHaveTextContent('XFRA');
    expect(evidenceValue(reference, 'Provider-Platzcode')).toHaveTextContent('FRA');
    expect(evidenceValue(reference, 'Historische Listing-ID')).toHaveTextContent(
      'historical-listing-a',
    );
    expect(evidenceValue(reference, 'Kursbeleg-Fingerprint')).toHaveTextContent(
      'historical-quote-fingerprint-a',
    );
    expect(evidenceValue(reference, 'Cachezustand zur Erfassung')).toHaveTextContent('HIT');
    expect(
      within(failure).getByText('Kein Kursbeleg für diese Erfassung gespeichert.'),
    ).toBeVisible();
    expect(within(failure).getByText('FRANKFURT_REQUEST_THROTTLED')).toBeVisible();
    expect(evidenceValue(failure, 'Quellsegment / Identität')).toHaveTextContent('route-b');
    expect(evidenceValue(failure, 'Originalkurszeit (UTC)')).toHaveTextContent('unbekannt');
    expect(evidenceValue(failure, 'Handelsplatz (MIC)')).toHaveTextContent('nicht übermittelt');
    expect(dataEvidenceApi.history).toHaveBeenCalledTimes(1);
  });
  it('keeps each segment, its counts including zero, and its capture bounds independently readable', async () => {
    vi.mocked(dataEvidenceApi.history).mockResolvedValue(recorded);
    open();
    load();
    await screen.findByText('Protokoll geladen.');
    const [first, second] = screen.getAllByRole('article');
    expect(evidenceValue(first, 'Erfasste Intervalle')).toHaveTextContent('2 UTC-Slots');
    expect(evidenceValue(first, 'Unterschiedliche Kursbelege')).toHaveTextContent('1 Kursbeleg');
    expect(evidenceValue(first, 'UTC-Tage mit Erfassung')).toHaveTextContent('1 UTC-Tag');
    expect(evidenceValue(second, 'Unterschiedliche Kursbelege')).toHaveTextContent('0 Kursbelege');
    expect(evidenceValue(first, 'Erste Erfassung im Fenster (UTC)')).toHaveTextContent(
      '2026-10-07T10:00:00Z',
    );
    expect(evidenceValue(second, 'Letzte Erfassung im Fenster (UTC)')).toHaveTextContent(
      '2026-10-07T10:06:00Z',
    );
    fireEvent.click(within(second).getByText('Statuszahlen dieses Quellsegments'));
    const table = within(second).getByRole('table');
    const zero = within(table).getByRole('row', { name: /TWO_SIDED_WITHIN_AGE_LIMIT 0/ });
    expect(within(zero).getByRole('cell')).toHaveTextContent('0');
    expect(within(zero).getByRole('rowheader')).toHaveAttribute('scope', 'row');
    expect(within(table).getByRole('columnheader', { name: 'Anzahl Intervalle' })).toHaveAttribute(
      'scope',
      'col',
    );
    expect(dataEvidenceApi.history).toHaveBeenCalledTimes(1);
  });
  it('makes the global detail limit distinct from the full window counters and earliest product capture', async () => {
    vi.mocked(dataEvidenceApi.history).mockResolvedValue({
      ...recorded,
      segments: recorded.segments.map((segment, i) => ({
        ...segment,
        sampled_slots: i === 0 ? 60 : 55,
      })),
      items: Array.from({ length: 50 }, (_, i) => ({
        ...recorded.items[i % 2],
        id: `sample-${i}`,
      })),
    });
    open();
    load();
    await screen.findByText('Protokoll geladen.');
    const report = screen.getByRole('region', { name: 'Gespeicherte Kursbeobachtungen' });
    expect(evidenceValue(report, 'Beginn des Erfassungsfensters (UTC)')).toHaveTextContent(
      empty.window_start,
    );
    expect(evidenceValue(report, 'Erste bekannte Produkterfassung (UTC)')).toHaveTextContent(
      '2026-09-01T10:00:00Z',
    );
    expect(observations()).toHaveLength(50);
    expect(screen.getByText(/Höchstens 50 zuletzt erfasste Beobachtungen/)).toHaveTextContent(
      'über alle Quellsegmente zusammen',
    );
    expect(screen.getByText(/Höchstens 50 zuletzt erfasste Beobachtungen/)).toHaveTextContent(
      'Die Segmentzähler gelten für das ganze Fenster',
    );
    const [first, second] = screen.getAllByRole('article');
    expect(evidenceValue(first, 'Erfasste Intervalle')).toHaveTextContent('60 UTC-Slots');
    expect(evidenceValue(second, 'Erfasste Intervalle')).toHaveTextContent('55 UTC-Slots');
    expect(
      screen.getByText(
        /Eine Anzahl erwarteter oder aus einer Kurshistorie ausgeschlossener Kurspunkte/,
      ),
    ).toBeVisible();
    expect(screen.queryByText(/\d+\s?%/)).not.toBeInTheDocument();
  });
  it('does not invent absent policy, venue, evidence identity or capability flags in older responses', async () => {
    vi.mocked(dataEvidenceApi.history).mockResolvedValue({
      ...empty,
      items: [
        {
          ...recorded.items[0],
          quote_fingerprint: undefined,
          quote: {
            bid: '.20',
            ask: '.22',
            reference_price: null,
            reference_price_type: null,
            currency: 'EUR',
            observed_at: '2026-10-07T09:58:00Z',
            source_mode: null,
          },
        },
      ],
    });
    open();
    load();
    await screen.findByText('Protokoll geladen.');
    const report = screen.getByRole('region', { name: 'Gespeicherte Kursbeobachtungen' });
    for (const label of [
      'Erfassungsregel',
      'Zeitabdeckungsquote',
      'IV-Historie verfügbar (Backendangabe)',
      'Synchrone Basiswertkurse verfügbar (Backendangabe)',
      'Für Ausführung verwendbar (Backendangabe)',
    ]) {
      expect(evidenceValue(report, label)).toHaveTextContent('nicht übermittelt');
    }
    expect(
      screen.queryByText(/Je Route und historischer Identität bleibt/),
    ).not.toBeInTheDocument();
    const [item] = observations();
    expect(evidenceValue(item, 'Originalkurszeit (UTC)')).toHaveTextContent('2026-10-07T09:58:00Z');
    expect(evidenceValue(item, 'Geldkurs (BID)')).toHaveTextContent('.20');
    expect(evidenceValue(item, 'Briefkurs (ASK)')).toHaveTextContent('.22');
    expect(evidenceValue(item, 'Referenzkurs')).toHaveTextContent('nicht vorhanden');
    for (const label of [
      'Handelsplatz (MIC)',
      'Provider-Platzcode',
      'Historische Listing-ID',
      'Kursbeleg-Fingerprint',
      'Zeitbasis der Quelle',
    ]) {
      expect(evidenceValue(item, label)).toHaveTextContent('nicht übermittelt');
    }
  });
  it('retains unknown status and policy codes without an invented success or frequency', async () => {
    vi.mocked(dataEvidenceApi.history).mockResolvedValue({
      ...recorded,
      sampling_policy: 'FUTURE_SAMPLING_POLICY',
      segments: [{ ...recorded.segments[0], statuses: { FUTURE_STATUS: 2 } }],
      items: [{ ...recorded.items[0], status: 'FUTURE_STATUS' }],
    });
    open();
    load();
    await screen.findByText('Protokoll geladen.');
    expect(screen.getByText('FUTURE_SAMPLING_POLICY')).toBeVisible();
    expect(
      screen.queryByText(/Je Route und historischer Identität bleibt/),
    ).not.toBeInTheDocument();
    fireEvent.click(screen.getByText('Statuszahlen dieses Quellsegments'));
    expect(
      screen.getByRole('row', { name: /Nicht eingeordneter Erfassungsstatus FUTURE_STATUS 2/ }),
    ).toBeVisible();
    const [item] = observations();
    expect(
      within(item).getByRole('heading', { name: /Nicht eingeordneter Erfassungsstatus/ }),
    ).toBeVisible();
    expect(within(item).getByText('FUTURE_STATUS')).toBeVisible();
  });
  it('normalizes only timezone-qualified instants to UTC and leaves uncertain source text untouched', async () => {
    vi.mocked(dataEvidenceApi.history).mockResolvedValue({
      ...recorded,
      items: [
        {
          ...recorded.items[0],
          captured_at: '2026-10-07T12:01:00+02:00',
          retrieved_at: '2026-10-07T09:59:00',
          quote: { ...recorded.items[0].quote!, observed_at: 'invalidZ' },
        },
      ],
    });
    open();
    load();
    await screen.findByText('Protokoll geladen.');
    const [item] = observations();
    expect(evidenceValue(item, 'Erfassungszeit (UTC)')).toHaveTextContent('2026-10-07T10:01:00Z');
    expect(evidenceValue(item, 'Erfassungszeit (UTC)')?.firstElementChild).toHaveAttribute(
      'datetime',
      '2026-10-07T12:01:00+02:00',
    );
    expect(evidenceValue(item, 'Abrufzeit (UTC)')).toHaveTextContent(
      '2026-10-07T09:59:00 · Zeitbasis nicht belegt',
    );
    expect(evidenceValue(item, 'Abrufzeit (UTC)')?.querySelector('time')).toBeNull();
    expect(evidenceValue(item, 'Originalkurszeit (UTC)')).toHaveTextContent(
      'invalidZ · Zeitbasis nicht belegt',
    );
    expect(evidenceValue(item, 'Originalzeittext der Quelle (unverändert)')).toHaveTextContent(
      '07.10.2026 11:30',
    );
  });
  it('keeps empty details and absent status counters explicit without treating them as an error-free history', async () => {
    vi.mocked(dataEvidenceApi.history).mockResolvedValue({
      ...empty,
      collection_started_at: recorded.collection_started_at,
      segments: [{ ...recorded.segments[0], statuses: {} }],
    });
    open();
    load();
    await screen.findByText('Protokoll geladen.');
    fireEvent.click(screen.getByText('Statuszahlen dieses Quellsegments'));
    expect(screen.getByText('Keine Statuszahlen übermittelt.')).toBeVisible();
    fireEvent.click(screen.getByText('Erfassungsbelege mit Originalzeiten (0 geliefert)'));
    expect(screen.getByText('Keine Detailbelege in dieser Antwort.')).toBeVisible();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(
      screen.queryByRole('list', { name: 'Einzelne gespeicherte Erfassungsbelege' }),
    ).not.toBeInTheDocument();
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
    expect(dataEvidenceApi.history).toHaveBeenCalledTimes(1);
    await act(() => {
      resolve(empty);
      return Promise.resolve();
    });
    expect(screen.queryByText(/Daraus folgt keine Entwarnung/)).not.toBeInTheDocument();
    vi.mocked(dataEvidenceApi.history).mockRejectedValueOnce(new Error('offline'));
    load();
    expect(await screen.findByRole('alert')).toHaveTextContent('kein neues Ergebnis');
    expect(dataEvidenceApi.history).toHaveBeenLastCalledWith('w', 31, expect.any(AbortSignal));
    vi.mocked(dataEvidenceApi.history).mockResolvedValueOnce(empty);
    load();
    expect(await screen.findByText(/Daraus folgt keine Entwarnung/)).toBeVisible();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(dataEvidenceApi.history).toHaveBeenCalledTimes(3);
  });
  it.each(['success', 'error'] as const)(
    'discards an old %s after a product A → B → A cycle',
    async (outcome) => {
      let resolve!: (value: QuoteHistoryReport) => void;
      let reject!: (reason: Error) => void;
      vi.mocked(dataEvidenceApi.history).mockImplementationOnce(
        () =>
          new Promise((done, failed) => {
            resolve = done;
            reject = failed;
          }),
      );
      const { rerender } = render(<WarrantQuoteHistory warrantId="w" />);
      fireEvent.click(screen.getByText('Kursdaten-Verfügbarkeit und Erfassungsprotokoll'));
      load();
      const signal = vi.mocked(dataEvidenceApi.history).mock.calls[0][2]!;
      rerender(<WarrantQuoteHistory warrantId="other" />);
      expect(signal.aborted).toBe(true);
      rerender(<WarrantQuoteHistory warrantId="w" />);
      fireEvent.click(screen.getByText('Kursdaten-Verfügbarkeit und Erfassungsprotokoll'));
      vi.mocked(dataEvidenceApi.history).mockResolvedValueOnce(empty);
      load();
      await screen.findByText(/Daraus folgt keine Entwarnung/);
      await act(() => {
        if (outcome === 'success') resolve(recorded);
        else reject(new Error('obsolete failure'));
        return Promise.resolve();
      });
      expect(screen.getByText(/Daraus folgt keine Entwarnung/)).toBeVisible();
      expect(screen.queryByRole('article')).not.toBeInTheDocument();
      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
      expect(dataEvidenceApi.history).toHaveBeenCalledTimes(2);
    },
  );
  it('clears a completed result or error on product changes without an automatic read', async () => {
    vi.mocked(dataEvidenceApi.history).mockResolvedValueOnce(recorded);
    const { rerender } = render(<WarrantQuoteHistory warrantId="w" />);
    fireEvent.click(screen.getByText('Kursdaten-Verfügbarkeit und Erfassungsprotokoll'));
    load();
    await screen.findByText('Protokoll geladen.');
    rerender(<WarrantQuoteHistory warrantId="other" />);
    expect(
      screen.queryByRole('region', { name: 'Gespeicherte Kursbeobachtungen' }),
    ).not.toBeInTheDocument();
    expect(dataEvidenceApi.history).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByText('Kursdaten-Verfügbarkeit und Erfassungsprotokoll'));
    vi.mocked(dataEvidenceApi.history).mockRejectedValueOnce(new Error('offline'));
    load();
    await screen.findByRole('alert');
    rerender(<WarrantQuoteHistory warrantId="w" />);
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(dataEvidenceApi.history).toHaveBeenCalledTimes(2);
  });
  it('rejects a response for a different product instead of displaying its evidence', async () => {
    vi.mocked(dataEvidenceApi.history).mockResolvedValue({ ...recorded, warrant_id: 'foreign' });
    open();
    load();
    expect(await screen.findByRole('alert')).toHaveTextContent('gehört zu einem anderen Produkt');
    expect(
      screen.queryByRole('region', { name: 'Gespeicherte Kursbeobachtungen' }),
    ).not.toBeInTheDocument();
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
