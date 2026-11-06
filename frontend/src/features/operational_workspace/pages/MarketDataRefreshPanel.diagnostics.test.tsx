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

const sourceCheck = {
  ...baseCheck,
  kind: 'SOURCE',
  source: 'FRANKFURT_QUOTES',
  listing_id: 'listing-diagnostic',
  identity_key: 'a'.repeat(64),
  category: 'PROVIDER_ERROR',
  reason: 'FRANKFURT_TRANSPORT_TIMEOUT',
  attempt_started_at: firstFailure,
  provider_reachable: false,
  response_valid: null,
  quote_usable: true,
  qualified_success: false,
  retained_quote: true,
  quote_status: 'LAST_AVAILABLE',
  quote_observed_at: firstFailure,
  quote_retrieved_at: firstFailure,
};

function sourceStatus(
  changes: Record<string, unknown> = {},
  jobChanges: Record<string, unknown> = {},
) {
  return {
    ...sample,
    jobs: [
      {
        ...job,
        checked_at: lastFailure,
        diagnostics: { scope: 'PROCESS_LOCAL', checks: [{ ...sourceCheck, ...changes }] },
        ...jobChanges,
      },
    ],
  };
}

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
      'Seit: 30.10.2026, 10:00:00 UTC · Zuletzt festgestellt: 30.10.2026, 10:05:00 UTC',
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
      'Start: 30.10.2026, 10:10:00 UTC · bisher 62 Sek. · Stand der Statusabfrage',
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
        'Kurszeit: 30.10.2026, 10:05:00 UTC · Abrufzeit des Kurses: 30.10.2026, 10:10:00 UTC',
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
                last_failure_reason: 'FRANKFURT_TRANSPORT_TIMEOUT',
                last_failure_category: 'PROVIDER_ERROR',
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
    expect(screen.getByText('Vorheriger Befund: FRANKFURT_TRANSPORT_TIMEOUT')).toBeVisible();
    expect(screen.getByText('Letzte Fehlerkategorie: PROVIDER_ERROR')).toBeVisible();
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
    expect(
      screen.getByText('Historischer Beleg · In letzter Prüfung nicht erneut geprüft.'),
    ).toBeVisible();
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
    expect(
      screen.getByText('Historischer Beleg · In letzter Prüfung nicht erneut geprüft.'),
    ).toBeVisible();
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

  it.each([
    [false, null, true, false, 'Nein', 'Nicht belegt', 'Ja', 'Nein'],
    [true, false, false, false, 'Ja', 'Nein', 'Nein', 'Nein'],
    [null, true, true, true, 'Nicht belegt', 'Ja', 'Ja', 'Ja'],
    [
      undefined,
      undefined,
      null,
      undefined,
      'Nicht belegt',
      'Nicht belegt',
      'Nicht belegt',
      'Nicht belegt',
    ],
  ])(
    'keeps transport %s, response %s, quote %s and qualification %s independent',
    async (reachable, valid, usable, success, reachText, validText, usableText, successText) => {
      await loadStatus(
        sourceStatus({
          provider_reachable: reachable,
          response_valid: valid,
          quote_usable: usable,
          qualified_success: success,
          retained_quote: undefined,
        }),
      );

      const check = within(screen.getByRole('list', { name: 'Abgeschlossene Diagnosebelege' }));
      expect(check.getByText(`Provider technisch erreichbar: ${reachText}`)).toBeVisible();
      expect(check.getByText(`Antwort gültig: ${validText}`)).toBeVisible();
      expect(check.getByText(`Kurs verwendbar: ${usableText}`)).toBeVisible();
      expect(check.getByText(`Qualifizierter Erfolg dieser Prüfung: ${successText}`)).toBeVisible();
      expect(check.getByText('Gespeicherter Ersatzkurs: Nicht belegt')).toBeVisible();
      expect(check.getAllByRole('term')).toHaveLength(6);
      expect(check.getAllByRole('definition')).toHaveLength(6);
      expect(check.queryByRole('alert')).not.toBeInTheDocument();
      expect(
        screen.queryByText(/Provider wieder erreichbar|Kursversorgung wiederhergestellt/),
      ).not.toBeInTheDocument();
      expect(request).toHaveBeenCalledTimes(1);
    },
  );

  it('keeps a new failure episode visible when the payload also contains an earlier recovery', async () => {
    await loadStatus(
      sourceStatus({
        first_failure_at: lastFailure,
        last_failure_at: recovered,
        last_checked_at: recovered,
        recovered_at: firstFailure,
        last_success_at: firstFailure,
      }),
    );

    expect(screen.getByText('Providerfehler · 2 Prüfungen in Folge mit Befund')).toBeVisible();
    const historic = screen.getByText(/Früherer Wiederherstellungsbeleg:/);
    expect(historic).toHaveTextContent('Die gemeldete Fehlerfolge bleibt bestehen.');
    expect(historic.querySelector('time')).toHaveAttribute('datetime', firstFailure);
    expect(
      screen.queryByText(/Kursversorgung wiederhergestellt|Provider wieder erreichbar/),
    ).not.toBeInTheDocument();
    expect(screen.getByText('Qualifizierter Erfolg dieser Prüfung: Nein')).toBeVisible();
  });

  it('retains each source identity and its own completed attempt while a new job is running', async () => {
    const newerIdentity = 'b'.repeat(64);
    await loadStatus(
      sourceStatus(
        {},
        {
          execution: { running: true, started_at: recovered, elapsed_seconds: 0 },
          diagnostics: {
            scope: 'PROCESS_LOCAL',
            checks: [
              { ...sourceCheck, observed_in_latest_run: false },
              {
                ...sourceCheck,
                identity_key: newerIdentity,
                attempt_started_at: lastFailure,
                last_checked_at: recovered,
                observed_in_latest_run: true,
                qualified_success: true,
                provider_reachable: null,
                response_valid: true,
                consecutive_failures: 0,
                retained_quote: false,
                reason: null,
                category: null,
                last_failure_at: null,
              },
            ],
          },
        },
      ),
    );

    const list = screen.getByRole('list', { name: 'Abgeschlossene Diagnosebelege' });
    const [older, latest] = within(list).getAllByRole('listitem');
    expect(within(older).getByText(`Quellenidentität: ${sourceCheck.identity_key}`)).toBeVisible();
    expect(within(latest).getByText(`Quellenidentität: ${newerIdentity}`)).toBeVisible();
    expect(
      within(older).getByText(/Historischer Beleg · In letzter Prüfung nicht erneut geprüft/),
    ).toBeVisible();
    expect(within(latest).getByText('Beleg aus dem letzten abgeschlossenen Lauf.')).toBeVisible();
    expect(
      within(older)
        .getByText(/Beginn dieses Quellenversuchs:/)
        .querySelector('time'),
    ).toHaveAttribute('datetime', firstFailure);
    expect(
      within(latest)
        .getByText(/Beginn dieses Quellenversuchs:/)
        .querySelector('time'),
    ).toHaveAttribute('datetime', lastFailure);
    expect(
      within(older)
        .getByText(/Letzte Quellen- oder Auftragsprüfung:/)
        .querySelector('time'),
    ).toHaveAttribute('datetime', lastFailure);
    expect(
      within(latest)
        .getByText(/Letzte Quellen- oder Auftragsprüfung:/)
        .querySelector('time'),
    ).toHaveAttribute('datetime', recovered);
    expect(
      screen.getByText(/Letzter abgeschlossener Schedulerlauf:/).querySelector('time'),
    ).toHaveAttribute('datetime', lastFailure);
    expect(screen.getByText(/Aktueller Abruf · Start:/)).toHaveTextContent('bisher 0 Sek.');
    expect(screen.getByText(/Aktueller Abruf · Start:/).querySelector('time')).toHaveAttribute(
      'datetime',
      recovered,
    );
    expect(
      within(older).queryByText('Qualifizierter Erfolg dieser Prüfung: Ja'),
    ).not.toBeInTheDocument();
    expect(request).toHaveBeenCalledTimes(1);
  });

  it('preserves unknown original codes and missing qualification without inventing an assessment', async () => {
    await loadStatus(
      sourceStatus({
        status: 'FUTURE_STATUS',
        category: 'FUTURE_CATEGORY',
        reason: 'FUTURE_REASON',
        quote_status: 'FUTURE_QUOTE_STATUS',
        qualified_success: undefined,
        observed_in_latest_run: undefined,
        listing_id: null,
        identity_key: null,
      }),
    );

    expect(screen.getByText(/Statuscode: FUTURE_STATUS/)).toBeVisible();
    expect(screen.getByText('Diagnosekategorie: FUTURE_CATEGORY')).toBeVisible();
    expect(screen.getByText('Diagnosecode: FUTURE_REASON')).toBeVisible();
    expect(screen.getByText('Kursstatuscode: FUTURE_QUOTE_STATUS')).toBeVisible();
    expect(screen.getByText('Kursstatus derzeit nicht einordenbar')).toBeVisible();
    expect(screen.getByText('Qualifizierter Erfolg dieser Prüfung: Nicht belegt')).toBeVisible();
    expect(screen.getByText('Notierung: Nicht belegt')).toBeVisible();
    expect(screen.getByText('Quellenidentität: Nicht belegt')).toBeVisible();
    expect(
      screen.getByText('Zuordnung zum letzten abgeschlossenen Lauf nicht belegt.'),
    ).toBeVisible();
    expect(
      screen.queryByText(/Provider wieder erreichbar|Kursversorgung wiederhergestellt/),
    ).not.toBeInTheDocument();
  });

  it('renders supplied cache outcomes as separate evidence without joining them to an older check', async () => {
    const cases = [
      ['HIT', 'Cachetreffer · HIT'],
      ['MISS', 'Kein Cachetreffer · MISS'],
      ['BYPASS', 'Cache nicht verwendet · BYPASS'],
      ['STALE_REJECTED', 'Veralteter Cacheeintrag verworfen · STALE_REJECTED'],
      ['FUTURE_CACHE', 'Cachezustand derzeit nicht einordenbar · FUTURE_CACHE'],
      [null, 'Nicht belegt'],
    ];
    await loadStatus(
      sourceStatus(
        { observed_in_latest_run: false },
        {
          quotes: cases.map(([status], index) => ({
            provider: 'FRANKFURT_QUOTES',
            warrant_listing_id: 'listing-diagnostic',
            identity_key: `cache-identity-${index}`,
            cache_status: status,
            retrieved_at: firstFailure,
            attempt_completed_at: recovered,
          })),
        },
      ),
    );
    fireEvent.click(screen.getByText('Cachebelege des letzten abgeschlossenen Laufs'));

    const checks = screen.getByRole('list', { name: 'Abgeschlossene Diagnosebelege' });
    const cache = screen.getByRole('list', { name: 'Gelieferte Cachebelege' });
    const rows = within(cache).getAllByRole('listitem');
    expect(rows).toHaveLength(cases.length);
    cases.forEach(([, label], index) => {
      expect(within(rows[index]).getByText(label!)).toBeVisible();
      expect(within(rows[index]).getByText(`cache-identity-${index}`)).toBeVisible();
      expect(rows[index].querySelectorAll('time')).toHaveLength(2);
      expect(rows[index].querySelector('time')).toHaveAttribute('datetime', firstFailure);
    });
    expect(within(checks).queryByText(/cache-identity-/)).not.toBeInTheDocument();
    expect(within(checks).getByText('Qualifizierter Erfolg dieser Prüfung: Nein')).toBeVisible();
    expect(within(checks).getByText('Provider technisch erreichbar: Nein')).toBeVisible();
    expect(screen.queryByText(/Kursversorgung wiederhergestellt/)).not.toBeInTheDocument();
    expect(request).toHaveBeenCalledTimes(1);
  });

  it.each([
    [undefined, 'Cachebelege wurden in dieser Statusantwort nicht mitgeliefert.'],
    [null, 'Cachebelege wurden in dieser Statusantwort nicht mitgeliefert.'],
    [[], 'Keine Kursantworten für diesen abgeschlossenen Lauf geliefert.'],
  ])('keeps absent or empty cache evidence %s explicit', async (quotes, message) => {
    await loadStatus(sourceStatus({}, { quotes }));
    fireEvent.click(screen.getByText('Cachebelege des letzten abgeschlossenen Laufs'));
    expect(screen.getByText(message)).toBeVisible();
    expect(screen.queryByRole('list', { name: 'Gelieferte Cachebelege' })).not.toBeInTheDocument();
    expect(screen.getByText('Gespeicherter Ersatzkurs: Ja')).toBeVisible();
    expect(
      screen.queryByText(/Cachetreffer · HIT|Cache nicht verwendet · BYPASS/),
    ).not.toBeInTheDocument();
  });

  it('does not turn missing scope or an empty process snapshot into healthy providers', async () => {
    await loadStatus(sourceStatus({}, { diagnostics: { checks: [] } }));
    expect(screen.getByText('Geltungsbereich: Nicht belegt')).toBeVisible();
    expect(
      screen.getByText('Keine abgeschlossenen Diagnosebelege in dieser Statusantwort.'),
    ).toBeVisible();
    expect(
      screen.queryByText(/nur für diese Backend-Laufzeit|Kursversorgung wiederhergestellt/),
    ).not.toBeInTheDocument();
    expect(screen.queryByText('Provider technisch erreichbar: Ja')).not.toBeInTheDocument();
  });

  it('keeps missing or unqualified times without a synthetic instant', async () => {
    await loadStatus(
      sourceStatus({
        attempt_started_at: '10:15',
        last_checked_at: null,
        quote_observed_at: '2026-10-30T10:00:00',
        quote_retrieved_at: 'invalid-provider-time',
        quote_status: undefined,
      }),
    );
    const start = screen.getByText(/Beginn dieses Quellenversuchs:/);
    expect(start).toHaveTextContent('10:15 · Zeitbasis nicht belegt');
    expect(start.querySelector('time')).toBeNull();
    const quote = screen.getByText(/Kurszeit:/);
    expect(quote).toHaveTextContent('2026-10-30T10:00:00 · Zeitbasis nicht belegt');
    expect(quote).toHaveTextContent('invalid-provider-time · Zeitbasis nicht belegt');
    expect(quote.querySelector('time')).toBeNull();
    expect(screen.getByText(/Letzte Quellen- oder Auftragsprüfung:/)).toHaveTextContent(
      'Unbekannt',
    );
    expect(screen.getByText('Kursbewertung nicht mitgeliefert')).toBeVisible();
    expect(screen.queryByText('Kursqualität nicht geprüft')).not.toBeInTheDocument();
    expect(screen.queryByText(/Invalid Date/)).not.toBeInTheDocument();
  });

  it('keeps native disclosure and focus changes passive and clears old evidence on a failed reread', async () => {
    await loadStatus(sourceStatus({}, { quotes: [] }));
    const diagnostics = screen.getByText(/^Diagnose ·/);
    const cache = screen.getByText('Cachebelege des letzten abgeschlossenen Laufs');
    cache.focus();
    fireEvent.click(cache);
    expect(cache).toHaveFocus();
    expect(cache.parentElement).toHaveAttribute('open');
    fireEvent.click(cache);
    diagnostics.focus();
    fireEvent.click(diagnostics);
    fireEvent.click(diagnostics);
    expect(diagnostics).toHaveFocus();
    expect(request).toHaveBeenCalledTimes(1);
    expect(request).toHaveBeenLastCalledWith(
      expect.stringContaining('/market-data/refresh/status'),
    );

    request.mockRejectedValueOnce(new Error('unavailable'));
    fireEvent.click(screen.getByRole('button', { name: 'Abrufstatus laden' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Abrufstatus konnte nicht geladen werden.',
    );
    expect(
      screen.queryByRole('list', { name: 'Abgeschlossene Diagnosebelege' }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText(`Quellenidentität: ${sourceCheck.identity_key}`),
    ).not.toBeInTheDocument();
    expect(request).toHaveBeenCalledTimes(2);
    expect(request.mock.calls.every(([url]) => url.endsWith('/market-data/refresh/status'))).toBe(
      true,
    );
  });
});
