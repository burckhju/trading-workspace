import { fireEvent, render, screen, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { requestJson } from '../../market/services/http';
import { MarketDataRefreshPanel } from './MarketDataRefreshPanel';

vi.mock('../../market/services/http', () => ({ requestJson: vi.fn() }));
const request = vi.mocked(requestJson);
const firstFailure = '2026-10-30T10:00:00Z';
const lastFailure = '2026-10-30T10:05:00Z';
const recovered = '2026-10-30T10:10:00Z';
const baseCheck = {
  kind: 'JOB',
  source: null as string | null,
  listing_id: null as string | null,
  status: 'ERROR',
  category: 'JOB_ERROR' as string | null,
  reason: 'REFRESH_JOB_FAILED' as string | null,
  consecutive_failures: 2,
  first_failure_at: firstFailure as string | null,
  last_failure_at: lastFailure as string | null,
  last_success_at: null as string | null,
  recovered_at: null as string | null,
  last_checked_at: lastFailure as string | null,
  observed_in_latest_run: true,
};
const job = {
  job: 'WARRANT_QUOTES:held',
  name: 'Synthetic call',
  isin: 'DE000AB00001',
  status: 'ERROR',
  reason: 'REFRESH_JOB_FAILED',
  next_run_at: recovered,
};
const sample = {
  enabled: true,
  running: false,
  leader: true,
  last_error: null,
  settings: {
    warrants_interval_seconds: 300,
    underlyings_interval_seconds: 3600,
    discovery_interval_seconds: 3600,
  },
  jobs: [{ ...job, diagnostics: { scope: 'PROCESS_LOCAL', checks: [baseCheck] } }],
};

async function loadStatus(value: unknown = sample) {
  request.mockResolvedValue(value);
  render(<MarketDataRefreshPanel />);
  expect(request).not.toHaveBeenCalled();
  fireEvent.click(screen.getByText('Automatischer Kursabruf'));
  fireEvent.click(screen.getByRole('button', { name: 'Abrufstatus laden' }));
  await screen.findByText(/Synthetic call/);
  fireEvent.click(screen.getByText(/^Diagnose(?: ·|$)/));
}

beforeEach(() => vi.resetAllMocks());

describe('market data refresh operational diagnostics', () => {
  it('shows a repeated job failure with the original failure clocks and process scope', async () => {
    await loadStatus();

    expect(screen.getByText('Auftragsfehler · 2 Prüfungen in Folge mit Befund')).toBeVisible();
    expect(screen.getByText(/Seit:/)).toHaveTextContent(
      `Seit: ${new Date(firstFailure).toLocaleString('de-DE')} · Zuletzt festgestellt: ${new Date(lastFailure).toLocaleString('de-DE')}`,
    );
    expect(screen.getByText('Diagnosecode: REFRESH_JOB_FAILED')).toBeVisible();
    expect(screen.getByText(/nur für diese Backend-Laufzeit/)).toHaveTextContent(
      'werden bei einem Neustart zurückgesetzt',
    );
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(request).toHaveBeenCalledTimes(1);
  });

  it('separates the current retry duration from the previous failed checks', async () => {
    await loadStatus({
      ...sample,
      running: true,
      jobs: [
        {
          ...sample.jobs[0],
          execution: { running: true, started_at: recovered, elapsed_seconds: 62.8 },
        },
      ],
    });

    expect(screen.getByText(/^Abruf läuft · Nächste Prüfung frühestens/)).toBeVisible();
    expect(screen.getByText(/Aktueller Abruf · Start:/)).toHaveTextContent(
      `Start: ${new Date(recovered).toLocaleString('de-DE')} · bisher 62 Sek. · Stand der Statusabfrage`,
    );
    expect(screen.getByText('Auftragsfehler · 2 Prüfungen in Folge mit Befund')).toBeVisible();
    expect(screen.getByText(/Letzte Quellen- oder Auftragsprüfung:/)).toHaveTextContent(
      new Date(lastFailure).toLocaleString('de-DE'),
    );
    expect(screen.queryByText(/hängt|hängend|Zeitlimit überschritten/i)).not.toBeInTheDocument();
  });

  it('reports recovery on a subsequent explicit read without claiming a fresh quote', async () => {
    await loadStatus();
    request.mockResolvedValue({
      ...sample,
      jobs: [
        {
          ...job,
          status: 'AVAILABLE',
          reason: 'QUOTE_OBSERVATIONS_AVAILABLE',
          execution: { running: false, started_at: null, elapsed_seconds: null },
          diagnostics: {
            scope: 'PROCESS_LOCAL',
            checks: [
              {
                ...baseCheck,
                status: 'AVAILABLE',
                category: null,
                reason: null,
                consecutive_failures: 0,
                recovered_at: recovered,
                last_checked_at: recovered,
              },
            ],
          },
        },
      ],
    });
    fireEvent.click(screen.getByRole('button', { name: 'Abrufstatus laden' }));

    expect(await screen.findByText(/Auftrag wieder abgeschlossen:/)).toHaveTextContent(
      new Date(recovered).toLocaleString('de-DE'),
    );
    expect(screen.queryByText(/Prüfungen in Folge mit Befund/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Aktueller Abruf · Start:/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Kurs wieder frisch|Frischer Kurs/)).not.toBeInTheDocument();
    expect(screen.getByText(/Das Kursalter steht separat/)).toBeVisible();
    expect(request).toHaveBeenCalledTimes(2);
  });

  it('keeps a retained provider failure visible beside another successful provider', async () => {
    await loadStatus({
      ...sample,
      jobs: [
        {
          ...job,
          status: 'AVAILABLE',
          reason: 'QUOTE_OBSERVATIONS_AVAILABLE',
          diagnostics: {
            scope: 'PROCESS_LOCAL',
            checks: [
              { ...baseCheck, status: 'AVAILABLE', category: null, consecutive_failures: 0 },
              {
                ...baseCheck,
                kind: 'SOURCE',
                source: 'VONTOBEL_MARKETS',
                listing_id: 'listing-success',
                status: 'AVAILABLE',
                category: null,
                reason: 'VALID_BID_AVAILABLE',
                consecutive_failures: 0,
              },
              {
                ...baseCheck,
                kind: 'SOURCE',
                source: 'FRANKFURT_QUOTES',
                listing_id: 'listing-retained',
                status: 'AVAILABLE',
                category: 'PROVIDER_ERROR',
                reason: 'FRANKFURT_HTTP_503',
                retained_quote: true,
                qualified_success: false,
                quote_status: 'FRESH',
                quote_usable: true,
                provider_reachable: true,
                response_valid: false,
                quote_observed_at: firstFailure,
                quote_retrieved_at: firstFailure,
                last_success_at: firstFailure,
              },
            ],
          },
        },
      ],
    });

    expect(
      screen.getByText(/^Schedulerlauf abgeschlossen · Nächste Prüfung frühestens/),
    ).toBeVisible();
    expect(screen.getByText(/Offene Quellenbefunde/)).toBeVisible();
    expect(screen.queryByText(/^Erfolgreich/)).not.toBeInTheDocument();
    expect(screen.getByText('FRANKFURT_QUOTES')).toBeVisible();
    expect(screen.getByText('Providerfehler · 2 Prüfungen in Folge mit Befund')).toBeVisible();
    expect(screen.getByText('Diagnosecode: FRANKFURT_HTTP_503')).toBeVisible();
    expect(screen.getByText('Notierung: listing-retained')).toBeVisible();
    expect(screen.getByText(/Gespeicherter Ersatzkurs vorhanden/)).toBeVisible();
    expect(screen.getByText('Qualifizierter Erfolg dieser Prüfung: Nein')).toBeVisible();
    expect(screen.getByText('Kurs innerhalb Altersgrenze')).toBeVisible();
    expect(screen.getByText('Antwort gültig: Nein')).toBeVisible();
    expect(screen.queryByText(/Kursversorgung wiederhergestellt/)).not.toBeInTheDocument();
    expect(screen.getByText('Notierung: listing-success')).toBeVisible();
  });

  it.each(['FRESH', 'LAST_AVAILABLE'])(
    'shows %s source evidence and the last qualified success even before a failure occurred',
    async (quoteStatus) => {
      await loadStatus({
        ...sample,
        jobs: [
          {
            ...job,
            status: 'AVAILABLE',
            diagnostics: {
              scope: 'PROCESS_LOCAL',
              checks: [
                {
                  ...baseCheck,
                  kind: 'SOURCE',
                  source: 'VONTOBEL_MARKETS',
                  listing_id: 'listing-fresh',
                  identity_key: 'warrant-listing-currency-mapping',
                  status: 'AVAILABLE',
                  category: null,
                  reason: null,
                  consecutive_failures: 0,
                  first_failure_at: null,
                  last_failure_at: null,
                  last_success_at: recovered,
                  last_checked_at: recovered,
                  qualified_success: true,
                  retained_quote: false,
                  quote_status: quoteStatus,
                  quote_usable: true,
                  quote_observed_at: lastFailure,
                  quote_retrieved_at: recovered,
                  provider_reachable: null,
                  response_valid: true,
                },
              ],
            },
          },
        ],
      });

      expect(screen.getByText('Provider technisch erreichbar: Nicht belegt')).toBeVisible();
      expect(screen.getByText('Antwort gültig: Ja')).toBeVisible();
      expect(screen.getByText('Kurs verwendbar: Ja')).toBeVisible();
      expect(screen.getByText('Qualifizierter Erfolg dieser Prüfung: Ja')).toBeVisible();
      expect(screen.getByText(/Letzter qualifizierter Kursabruf:/)).toHaveTextContent(
        new Date(recovered).toLocaleString('de-DE'),
      );
      expect(screen.getByText(/Kurszeit:/)).toHaveTextContent(
        `Kurszeit: ${new Date(lastFailure).toLocaleString('de-DE')} · Abrufzeit des Kurses: ${new Date(recovered).toLocaleString('de-DE')}`,
      );
      expect(screen.getByText('Quellenidentität: warrant-listing-currency-mapping')).toBeVisible();
      expect(
        screen.queryByText(
          /Letzter fehlgeschlagener Abruf|Kursversorgung wiederhergestellt|Offene Quellenbefunde/,
        ),
      ).not.toBeInTheDocument();
    },
  );

  it('keeps the last failure visible after a qualified source recovery', async () => {
    await loadStatus({
      ...sample,
      jobs: [
        {
          ...job,
          status: 'AVAILABLE',
          diagnostics: {
            scope: 'PROCESS_LOCAL',
            checks: [
              {
                ...baseCheck,
                kind: 'SOURCE',
                source: 'FRANKFURT_QUOTES',
                listing_id: 'listing-recovered',
                status: 'AVAILABLE',
                category: null,
                reason: null,
                consecutive_failures: 0,
                first_failure_at: null,
                last_success_at: recovered,
                recovered_at: recovered,
                last_checked_at: recovered,
                qualified_success: true,
                quote_status: 'FRESH',
                quote_usable: true,
                provider_reachable: true,
                response_valid: true,
              },
            ],
          },
        },
      ],
    });

    expect(screen.getByText(/Kursversorgung wiederhergestellt:/)).toHaveTextContent(
      new Date(recovered).toLocaleString('de-DE'),
    );
    expect(screen.getByText(/Letzter fehlgeschlagener Abruf:/)).toHaveTextContent(
      new Date(lastFailure).toLocaleString('de-DE'),
    );
    expect(
      screen.queryByText(/Offene Quellenbefunde|Auftrag wieder abgeschlossen/),
    ).not.toBeInTheDocument();
  });

  it.each([
    ['STALE', 'Kurs veraltet'],
    ['MISSING', 'Kurs fehlt'],
    ['INVALID', 'Ungültige Kursdaten'],
    ['REFERENCE_ONLY', 'Nur Referenzkurs'],
    ['TIMESTAMP_UNKNOWN', 'Kurszeitpunkt nicht belegt'],
    ['LAST_AVAILABLE', 'Letzter verfügbarer Kurs gemäß Sitzungsbewertung'],
  ])('shows %s without asserting a recovered source', async (quoteStatus, label) => {
    await loadStatus({
      ...sample,
      jobs: [
        {
          ...job,
          status: 'AVAILABLE',
          diagnostics: {
            scope: 'PROCESS_LOCAL',
            checks: [
              {
                ...baseCheck,
                kind: 'SOURCE',
                source: 'FRANKFURT_QUOTES',
                listing_id: 'listing-needs-review',
                status: 'AVAILABLE',
                category: 'DATA_QUALITY',
                quote_status: quoteStatus,
                qualified_success: false,
                last_success_at: firstFailure,
                quote_usable: false,
                provider_reachable: true,
                response_valid: true,
              },
            ],
          },
        },
      ],
    });

    expect(screen.getByText(label)).toBeVisible();
    expect(screen.getByText('Provider technisch erreichbar: Ja')).toBeVisible();
    expect(screen.getByText('Antwort gültig: Ja')).toBeVisible();
    expect(screen.getByText('Kurs verwendbar: Nein')).toBeVisible();
    expect(screen.getByText('Qualifizierter Erfolg dieser Prüfung: Nein')).toBeVisible();
    expect(screen.getByText(/Letzter qualifizierter Kursabruf:/)).toHaveTextContent(
      new Date(firstFailure).toLocaleString('de-DE'),
    );
    expect(screen.queryByText(/Kursversorgung wiederhergestellt/)).not.toBeInTheDocument();
  });

  it('shows a locally deferred provider check even when its raw status is ERROR', async () => {
    await loadStatus({
      ...sample,
      jobs: [
        {
          ...job,
          diagnostics: {
            scope: 'PROCESS_LOCAL',
            checks: [
              {
                ...baseCheck,
                kind: 'SOURCE',
                source: 'FRANKFURT_QUOTES',
                status: 'ERROR',
                waiting: true,
                reason: 'FRANKFURT_REQUEST_THROTTLED',
              },
            ],
          },
        },
      ],
    });
    expect(
      screen.getByText('Wiederholung zurückgestellt · vorheriger Befund bleibt offen.'),
    ).toBeVisible();
    expect(screen.queryByText(/Kursversorgung wiederhergestellt/)).not.toBeInTheDocument();
  });

  it('keeps an older cached quote distinct from a deferred retry and a recovery', async () => {
    await loadStatus({
      ...sample,
      jobs: [
        {
          ...job,
          status: 'AVAILABLE',
          diagnostics: {
            scope: 'PROCESS_LOCAL',
            checks: [
              {
                ...baseCheck,
                kind: 'SOURCE',
                source: 'FRANKFURT_QUOTES',
                status: 'AVAILABLE',
                waiting: true,
                reason: 'WARRANT_QUOTE_RECOVERY_NOT_OBSERVED',
                category: null,
                last_failure_category: 'PROVIDER_ERROR',
                last_failure_reason: 'FRANKFURT_HTTP_503',
                qualified_success: false,
                quote_retrieved_at: firstFailure,
              },
            ],
          },
        },
      ],
    });

    expect(
      screen.getByText('Kein neuer Erfolgsnachweis · vorheriger Befund bleibt offen.'),
    ).toBeVisible();
    expect(screen.getByText('Qualifizierter Erfolg dieser Prüfung: Nein')).toBeVisible();
    expect(screen.getByText('Providerfehler · 2 Prüfungen in Folge mit Befund')).toBeVisible();
    expect(
      screen.queryByText(/Wiederholung zurückgestellt|Kursversorgung wiederhergestellt/),
    ).not.toBeInTheDocument();
  });

  it('marks a previous source finding that was not rechecked as historical evidence', async () => {
    await loadStatus({
      ...sample,
      jobs: [
        {
          ...job,
          diagnostics: {
            scope: 'PROCESS_LOCAL',
            checks: [
              {
                ...baseCheck,
                kind: 'SOURCE',
                source: 'MORGAN_STANLEY',
                listing_id: 'listing-not-rechecked',
                category: 'NO_QUOTE',
                reason: 'NO_QUOTE_RETURNED',
                consecutive_failures: 1,
                observed_in_latest_run: false,
              },
            ],
          },
        },
      ],
    });

    expect(screen.getByText('Kein Kurs verfügbar · 1 Prüfung in Folge mit Befund')).toBeVisible();
    expect(screen.getByText('In letzter Prüfung nicht erneut geprüft.')).toBeVisible();
    expect(
      screen.queryByText(/Kursversorgung wiederhergestellt|Auftrag wieder abgeschlossen/),
    ).not.toBeInTheDocument();
  });

  it('preserves earlier failure evidence while a rate-limited retry is deferred', async () => {
    await loadStatus({
      ...sample,
      jobs: [
        {
          ...job,
          status: 'DEFERRED',
          reason: 'FRANKFURT_REQUEST_THROTTLED',
          diagnostics: {
            scope: 'PROCESS_LOCAL',
            checks: [
              {
                ...baseCheck,
                status: 'DEFERRED',
                category: null,
                reason: 'FRANKFURT_REQUEST_THROTTLED',
                last_failure_category: 'JOB_ERROR',
                last_failure_reason: 'REFRESH_JOB_FAILED',
                observed_in_latest_run: false,
              },
            ],
          },
        },
      ],
    });

    expect(screen.getByText(/Abruflimit erreicht · Wiederholung eingeplant/)).toBeVisible();
    expect(screen.getByText('Auftragsfehler · 2 Prüfungen in Folge mit Befund')).toBeVisible();
    expect(
      screen.getByText('Wiederholung zurückgestellt · vorheriger Befund bleibt offen.'),
    ).toBeVisible();
    expect(screen.getByText('In letzter Prüfung nicht erneut geprüft.')).toBeVisible();
    expect(screen.getByText('Vorheriger Befund: REFRESH_JOB_FAILED')).toBeVisible();
    expect(screen.getByText('Diagnosecode: FRANKFURT_REQUEST_THROTTLED')).toBeVisible();
    expect(
      screen.queryByText(/Kursversorgung wiederhergestellt|Auftrag wieder abgeschlossen/),
    ).not.toBeInTheDocument();
  });

  it('accepts earlier status responses without execution or diagnostic fields', async () => {
    await loadStatus({ ...sample, jobs: [{ ...job, status: 'MISSING' }] });

    expect(screen.getByText(/^Keine Kursdaten · Nächste Prüfung frühestens/)).toBeVisible();
    expect(screen.getByText('REFRESH_JOB_FAILED')).toBeVisible();
    expect(screen.queryByText(/Abrufnachweise/)).not.toBeInTheDocument();
    expect(screen.queryByText(/nur für diese Backend-Laufzeit/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Aktueller Abruf/)).not.toBeInTheDocument();
  });

  it('shows the progress and separate errors of all five scheduler lanes', async () => {
    const lanes = [
      ['ISSUER_DISCOVERY', 'Neue Emittentenprodukte'],
      ['ISSUER_QUOTES', 'Emittentenkurse'],
      ['WARRANTS', 'Optionsscheine'],
      ['WARRANT_DISCOVERY', 'Weitere Kursquellen zuordnen'],
      ['UNDERLYINGS', 'Basiswerte'],
    ];
    await loadStatus({
      ...sample,
      lanes: Object.fromEntries(
        lanes.map(([lane]) => [
          lane,
          {
            running: false,
            current_job: null,
            pending_jobs: 1,
            last_error: `${lane}_FAILED`,
          },
        ]),
      ),
    });

    for (const [lane, label] of lanes) {
      const row = screen.getByText(
        `${label}: Wartet auf nächste Prüfung · 1 Aufgabe ohne Erstprüfung`,
      );
      expect(within(row).getByText(`Letzter Fehler: ${lane}_FAILED`)).toBeVisible();
    }
  });
});
