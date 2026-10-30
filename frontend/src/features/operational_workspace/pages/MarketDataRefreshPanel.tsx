import { useState } from 'react';

import { environment } from '../../../services/environment';
import { requestJson } from '../../market/services/http';
import { QuoteCoveragePanel } from './QuoteCoveragePanel';

type RefreshCheck = {
  kind: 'JOB' | 'SOURCE';
  source: string | null;
  listing_id: string | null;
  status: string;
  category: string | null;
  reason: string | null;
  consecutive_failures: number;
  first_failure_at: string | null;
  last_failure_at: string | null;
  last_failure_reason?: string | null;
  last_failure_category?: string | null;
  last_success_at?: string | null;
  qualified_success?: boolean;
  retained_quote?: boolean;
  quote_status?: string;
  quote_observed_at?: string | null;
  quote_retrieved_at?: string | null;
  quote_usable?: boolean | null;
  provider_reachable?: boolean | null;
  response_valid?: boolean | null;
  identity_key?: string | null;
  waiting?: boolean;
  recovered_at: string | null;
  last_checked_at: string | null;
  observed_in_latest_run: boolean;
};

type RefreshStatus = {
  enabled: boolean;
  running: boolean;
  leader: boolean;
  last_error: string | null;
  current_job?: string | null;
  current_jobs?: Record<string, string | null>;
  lanes?: Record<
    string,
    {
      running: boolean;
      current_job: string | null;
      pending_jobs: number;
      due_jobs?: number;
      overdue_jobs?: number;
      max_overdue_seconds?: number;
      last_error: string | null;
    }
  >;
  pending_jobs?: number;
  settings: {
    warrants_interval_seconds: number;
    underlyings_interval_seconds: number;
    discovery_interval_seconds: number;
    auto_select_position_sources?: boolean;
    auto_discover_issuer_routes?: boolean;
  };
  jobs: Array<{
    job: string;
    name: string;
    isin: string | null;
    status: string;
    reason: string;
    next_run_at: string | null;
    held?: boolean;
    execution?: {
      running: boolean;
      started_at: string | null;
      elapsed_seconds: number | null;
    };
    diagnostics?: {
      scope: 'PROCESS_LOCAL';
      checks: RefreshCheck[];
    };
    source_selection?: {
      positions_checked: number;
      decisions_changed: number;
      statuses: Record<string, number>;
    } | null;
  }>;
};

const laneLabels = {
  ISSUER_DISCOVERY: 'Neue Emittentenprodukte',
  ISSUER_QUOTES: 'Emittentenkurse',
  WARRANTS: 'Optionsscheine',
  WARRANT_DISCOVERY: 'Weitere Kursquellen zuordnen',
  UNDERLYINGS: 'Basiswerte',
};

const categoryLabels: Record<string, string> = {
  JOB_ERROR: 'Auftragsfehler',
  PROVIDER_ERROR: 'Providerfehler',
  NO_QUOTE: 'Kein Kurs verfügbar',
  CONFIGURATION: 'Konfiguration oder Zuordnung prüfen',
  DATA_QUALITY: 'Kursqualität prüfen',
};

const quoteLabels: Record<string, string> = {
  FRESH: 'Kurs innerhalb Altersgrenze',
  LAST_AVAILABLE: 'Letzter verfügbarer Kurs gemäß Sitzungsbewertung',
  STALE: 'Kurs veraltet',
  REFERENCE_ONLY: 'Nur Referenzkurs',
  MISSING: 'Kurs fehlt',
  INVALID: 'Ungültige Kursdaten',
  TIMESTAMP_UNKNOWN: 'Kurszeitpunkt nicht belegt',
  UNASSESSED: 'Kursqualität nicht geprüft',
};

function date(value: string | null): string {
  return value ? new Date(value).toLocaleString('de-DE') : 'Unbekannt';
}

function evidence(value: boolean | null | undefined): string {
  return value === true ? 'Ja' : value === false ? 'Nein' : 'Nicht belegt';
}

function RefreshDiagnostics({ reason, checks = [] }: { reason: string; checks?: RefreshCheck[] }) {
  return (
    <details className="mt-1 text-xs text-slate-400">
      <summary>
        Diagnose
        {checks.length > 0 &&
          ` · ${checks.length} ${checks.length === 1 ? 'Abrufnachweis' : 'Abrufnachweise'}`}
      </summary>
      <p>{reason}</p>
      {checks.map((check) => (
        <div
          key={`${check.kind}:${check.source}:${check.listing_id}:${check.identity_key ?? ''}`}
          className="mt-2 break-words border-l border-slate-700 pl-2"
        >
          <p>{check.kind === 'JOB' ? 'Auftrag' : (check.source ?? 'Quelle unbekannt')}</p>
          {check.consecutive_failures > 0 ? (
            <>
              <p className="text-amber-200">
                {categoryLabels[check.last_failure_category ?? check.category ?? ''] ??
                  check.last_failure_category ??
                  check.category ??
                  'Abruf prüfen'}{' '}
                · {check.consecutive_failures}{' '}
                {check.consecutive_failures === 1 ? 'Prüfung' : 'Prüfungen'} in Folge mit Befund
              </p>
              <p>
                Seit: {date(check.first_failure_at)} · Zuletzt festgestellt:{' '}
                {date(check.last_failure_at)}
              </p>
              {check.last_failure_reason && check.last_failure_reason !== check.reason && (
                <p>Vorheriger Befund: {check.last_failure_reason}</p>
              )}
            </>
          ) : check.recovered_at ? (
            <p>
              {check.kind === 'SOURCE'
                ? 'Kursversorgung wiederhergestellt'
                : 'Auftrag wieder abgeschlossen'}
              : {date(check.recovered_at)}
            </p>
          ) : null}
          {(check.waiting || check.status === 'DEFERRED') && (
            <p>
              {check.reason === 'WARRANT_QUOTE_RECOVERY_NOT_OBSERVED'
                ? 'Kein neuer Erfolgsnachweis'
                : 'Wiederholung zurückgestellt'}
              {check.consecutive_failures > 0 && ' · vorheriger Befund bleibt offen'}.
            </p>
          )}
          <p>
            {check.kind === 'SOURCE'
              ? 'Letzter qualifizierter Kursabruf'
              : 'Letzter abgeschlossener Auftrag'}
            : {date(check.last_success_at ?? null)}
          </p>
          {check.last_failure_at && (
            <p>Letzter fehlgeschlagener Abruf: {date(check.last_failure_at)}</p>
          )}
          {check.kind === 'SOURCE' && (
            <>
              <p>Provider technisch erreichbar: {evidence(check.provider_reachable)}</p>
              <p>Antwort gültig: {evidence(check.response_valid)}</p>
              <p>Kurs verwendbar: {evidence(check.quote_usable)}</p>
              <p>{quoteLabels[check.quote_status ?? 'UNASSESSED'] ?? check.quote_status}</p>
              {check.retained_quote && (
                <p className="text-amber-200">
                  Gespeicherter Ersatzkurs vorhanden. Kein Nachweis eines aktuellen Providererfolgs.
                </p>
              )}
              <p>
                Kurszeit: {date(check.quote_observed_at ?? null)} · Abrufzeit des Kurses:{' '}
                {date(check.quote_retrieved_at ?? null)}
              </p>
              {check.qualified_success !== undefined && (
                <p>Qualifizierter Erfolg dieser Prüfung: {evidence(check.qualified_success)}</p>
              )}
            </>
          )}
          {!check.observed_in_latest_run && <p>In letzter Prüfung nicht erneut geprüft.</p>}
          <p>
            Letzte Quellen- oder Auftragsprüfung: {date(check.last_checked_at)} · {check.status}
          </p>
          {check.reason && <p>Diagnosecode: {check.reason}</p>}
          {check.listing_id && <p>Notierung: {check.listing_id}</p>}
          {check.identity_key && <p>Quellenidentität: {check.identity_key}</p>}
        </div>
      ))}
    </details>
  );
}

function statusLabel(status: string): string {
  if (status === 'NEEDS_MASTER_DATA') return 'Stammdaten ergänzen oder prüfen';
  if (status === 'PENDING') return 'Erster Abruf steht aus';
  if (status === 'DEFERRED') return 'Abruflimit erreicht · Wiederholung eingeplant';
  if (status === 'AVAILABLE') return 'Schedulerlauf abgeschlossen';
  if (status === 'MISSING') return 'Keine Kursdaten';
  if (status === 'BLOCKED') return 'Zuordnung oder Zugang fehlt';
  return 'Abruf prüfen';
}

function discoveryReason(reason: string): string | null {
  const messages: Record<string, string> = {
    ISSUER_ISIN_INVALID:
      'Die ISIN ist formal ungültig. Bitte mit den Originalunterlagen abgleichen.',
    ISSUER_LISTING_MISSING:
      'Es ist keine Notierung hinterlegt. In den Optionsscheinstammdaten einen belegten Handelsplatz und die Handelswährung ergänzen.',
    ISSUER_NO_ACTIVE_EUR_LISTING:
      'Es fehlt eine aktive EUR-Notierung mit aktivem Handelsplatz. Bitte die vorhandenen Notierungen prüfen.',
    ISSUER_MULTIPLE_ACTIVE_EUR_LISTINGS:
      'Mehrere aktive EUR-Notierungen passen. Die Emittentenroute benötigt eine eindeutig geprüfte Zuordnung.',
    ISSUER_RENDER_TERMS_REQUIRED:
      'Die Produktseite verlangt eine Bestätigung ihrer Nutzungsbedingungen. Die automatische Prüfung wurde angehalten.',
    ISSUER_RENDER_ACCESS_BLOCKED:
      'Der Anbieter hat den Seitenzugriff eingeschränkt. Die automatische Prüfung wurde angehalten.',
    ISSUER_PAGE_ACCESS_OR_RATE_LIMIT:
      'Der Anbieter hat den Zugriff eingeschränkt oder das Abruflimit erreicht. Eine spätere Prüfung ist eingeplant.',
    ISSUER_PAGE_ACCESS_BLOCKED:
      'Der Anbieter hat den Seitenzugriff eingeschränkt. Die automatische Prüfung wurde angehalten.',
    ISSUER_RENDER_TIMEOUT:
      'Die gerenderte Produktseite wurde nicht rechtzeitig vollständig geladen. Ein neuer Versuch ist eingeplant.',
    ISSUER_RENDER_PRODUCT_INCOMPLETE:
      'Die gerenderte Seite liefert noch keinen vollständigen eindeutigen Produktnachweis.',
    ISSUER_RENDERER_UNAVAILABLE:
      'Der Dienst zum Laden der Produktseiten ist derzeit nicht erreichbar.',
    PRODUCT_EXPIRED_SETTLEMENT_REVIEW_REQUIRED:
      'Für dieses Produkt ist eine Prüfung der Fälligkeit und Abwicklung erforderlich.',
  };
  return messages[reason] ?? null;
}

function taskLabel(job: string): string {
  if (job.startsWith('ISSUER_MAPPING:')) return 'Emittentenquelle prüfen';
  if (job.startsWith('ISSUER_QUOTES:')) return 'Emittentenkurse';
  if (job.startsWith('WARRANT_QUOTES:')) return 'Optionsscheinkurse';
  if (job.startsWith('UNDERLYING_EOD:')) return 'Basiswert · Tagesschlusskurse';
  return 'Kursquelle zuordnen';
}

export function MarketDataRefreshPanel() {
  const [value, setValue] = useState<RefreshStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function load() {
    setLoading(true);
    setError(null);
    setValue(null);
    try {
      setValue(
        await requestJson<RefreshStatus>(
          `${environment.apiBaseUrl}/api/v1/market-data/refresh/status`,
        ),
      );
    } catch {
      setError('Abrufstatus konnte nicht geladen werden.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <details className="mb-6 rounded-xl border border-slate-800 bg-slate-900/60 p-4">
      <summary className="cursor-pointer text-sm font-semibold text-slate-200">
        Automatischer Kursabruf
      </summary>
      <p className="mt-3 text-sm text-slate-400">
        Aktive Basiswerte und Optionsscheine werden in den konfigurierten Intervallen geprüft.
        Offene Positionen und ihre Basiswerte werden zuerst geprüft. Verfügbare Kurse behalten ihren
        ursprünglichen Kurszeitpunkt.
      </p>
      <button
        type="button"
        onClick={() => void load()}
        disabled={loading}
        className="mt-3 rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-200"
      >
        {loading ? 'Status wird geladen …' : 'Abrufstatus laden'}
      </button>
      {error && (
        <p role="alert" className="mt-3 text-sm text-amber-300">
          {error}
        </p>
      )}
      <QuoteCoveragePanel />
      {value && (
        <div className="mt-3 text-sm text-slate-300">
          <p>
            {!value.enabled
              ? 'Automatischer Kursabruf ist ausgeschaltet.'
              : value.running
                ? 'Kursabruf läuft.'
                : value.leader
                  ? 'Automatischer Kursabruf ist aktiv.'
                  : 'Kursabruf wartet auf den Hintergrunddienst.'}
          </p>
          <p className="mt-2">
            Optionsscheine: alle {value.settings.warrants_interval_seconds / 60} Min. · Basiswerte:
            alle {value.settings.underlyings_interval_seconds / 60} Min. · Neue Zuordnungen: alle{' '}
            {value.settings.discovery_interval_seconds / 60} Min.
          </p>
          <p className="mt-2 text-slate-400">
            Basiswerte: abgeschlossene Tagesschlusskurse. Anbieterlimits können den nächsten Abruf
            verzögern. Ein abgeschlossener Schedulerlauf bestätigt nicht den Erfolg jeder
            Kursquelle.
          </p>
          {value.jobs.some((job) => job.diagnostics) && (
            <p className="mt-2 text-xs text-slate-400">
              Abrufdiagnosen gelten nur für diese Backend-Laufzeit und werden bei einem Neustart
              zurückgesetzt. Das Kursalter steht separat unter „Kursquellen im Depot“.
            </p>
          )}
          <p className="mt-2 text-slate-400">
            {value.settings.auto_select_position_sources
              ? 'Quellenauswahl aktiv: Fehlende Quellenbindungen werden beim Kursabruf erneut geprüft. Eine eindeutige, verifizierte und aktivierte Quelle wird automatisch zugeordnet. Bestehende Auswahlen bleiben erhalten; mehrere passende Quellen erfordern eine Klärung.'
              : 'Automatische Wiederprüfung fehlender Quellenbindungen ist ausgeschaltet.'}
          </p>
          <p className="mt-2 text-slate-400">
            {value.settings.auto_discover_issuer_routes
              ? 'Emittentensuche aktiv: Neue Optionsscheine von J.P. Morgan und Morgan Stanley werden auf den offiziellen Produktseiten geprüft. Eine gültige ISIN, ein eindeutiger Produktnachweis und genau eine passende aktive EUR-Notierung sind erforderlich.'
              : 'Automatische Suche nach neuen Emittentenprodukten ist ausgeschaltet.'}
          </p>
          {value.enabled && value.lanes && (
            <ul className="mt-2 text-slate-400">
              {Object.entries(laneLabels).map(([lane, label]) => {
                const progress = value.lanes?.[lane];
                if (!progress) return null;
                return (
                  <li key={lane}>
                    {label}: {progress.running ? 'Abruf läuft' : 'Wartet auf nächste Prüfung'} ·{' '}
                    {progress.pending_jobs} {progress.pending_jobs === 1 ? 'Aufgabe' : 'Aufgaben'}{' '}
                    ohne Erstprüfung
                    {progress.due_jobs !== undefined && (
                      <>
                        {' '}
                        · {progress.due_jobs} fällig
                        {progress.overdue_jobs !== undefined && (
                          <> · davon {progress.overdue_jobs} überfällig</>
                        )}
                        {!!progress.max_overdue_seconds && (
                          <>
                            {' '}
                            · längster Rückstand {Math.ceil(progress.max_overdue_seconds / 60)} Min.
                          </>
                        )}
                      </>
                    )}
                    {progress.last_error && (
                      <p className="text-amber-300">Letzter Fehler: {progress.last_error}</p>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
          {value.pending_jobs !== undefined && value.pending_jobs > 0 && (
            <p className="mt-2">
              Noch {value.pending_jobs} Aufgaben ohne abgeschlossene Erstprüfung.
            </p>
          )}
          {value.last_error && (
            <p className="mt-2 text-amber-300">Letzte Prüfung fehlgeschlagen: {value.last_error}</p>
          )}
          <ul className="mt-3 divide-y divide-slate-800">
            {value.jobs.map((job) => (
              <li key={job.job} className="py-2">
                <p>
                  {job.name} · {job.isin ?? 'ISIN fehlt'} · {taskLabel(job.job)}
                  {job.held && ' · Offene Position'}
                </p>
                <p>
                  {(job.execution?.running ??
                  (Object.values(value.current_jobs ?? {}).includes(job.job) ||
                    value.current_job === job.job))
                    ? 'Abruf läuft'
                    : statusLabel(job.status)}
                  {job.next_run_at && (
                    <>
                      {' '}
                      · Nächste Prüfung frühestens{' '}
                      {new Date(job.next_run_at).toLocaleString('de-DE')}
                    </>
                  )}
                </p>
                {job.execution?.running && (
                  <p className="text-xs text-slate-400">
                    Aktueller Abruf · Start: {date(job.execution.started_at)}
                    {job.execution.elapsed_seconds !== null && (
                      <> · bisher {Math.floor(job.execution.elapsed_seconds)} Sek.</>
                    )}{' '}
                    · Stand der Statusabfrage
                  </p>
                )}
                {job.diagnostics?.checks.some(
                  (check) => check.kind === 'SOURCE' && check.consecutive_failures > 0,
                ) && (
                  <p className="mt-1 text-amber-200">
                    Offene Quellenbefunde · Einzelne Providerabrufe sind nicht als behoben
                    bestätigt. Details unter „Diagnose“.
                  </p>
                )}
                {discoveryReason(job.reason) && (
                  <p className="mt-1 text-amber-200">{discoveryReason(job.reason)}</p>
                )}
                {job.source_selection && job.source_selection.positions_checked > 0 && (
                  <p className="text-slate-400">
                    Quellenauswahl: {job.source_selection.positions_checked} Positionen geprüft ·{' '}
                    {job.source_selection.decisions_changed} Entscheidungen aktualisiert ·{' '}
                    {job.source_selection.statuses.SELECTED ?? 0} zugeordnet ·{' '}
                    {job.source_selection.statuses.NO_VERIFIED_QUOTE_SOURCE ?? 0} ohne Quelle ·{' '}
                    {job.source_selection.statuses.AMBIGUOUS_SOURCE ?? 0} mehrdeutig
                  </p>
                )}
                <RefreshDiagnostics reason={job.reason} checks={job.diagnostics?.checks} />
              </li>
            ))}
          </ul>
        </div>
      )}
    </details>
  );
}
