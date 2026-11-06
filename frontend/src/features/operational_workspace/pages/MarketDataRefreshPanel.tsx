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
  qualified_success?: boolean | null;
  retained_quote?: boolean | null;
  quote_status?: string | null;
  quote_observed_at?: string | null;
  quote_retrieved_at?: string | null;
  quote_usable?: boolean | null;
  provider_reachable?: boolean | null;
  response_valid?: boolean | null;
  identity_key?: string | null;
  attempt_started_at?: string | null;
  waiting?: boolean;
  recovered_at: string | null;
  last_checked_at: string | null;
  observed_in_latest_run?: boolean | null;
};

// These are already part of each completed job's quote payload. Keep them
// separate from checks: a current quote must not decorate an older identity.
type RefreshCacheEvidence = {
  provider?: string | null;
  warrant_listing_id?: string | null;
  identity_key?: string | null;
  cache_status?: string | null;
  retrieved_at?: string | null;
  attempt_completed_at?: string | null;
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
    checked_at?: string | null;
    quotes?: RefreshCacheEvidence[] | null;
    held?: boolean;
    execution?: {
      running: boolean;
      started_at: string | null;
      elapsed_seconds: number | null;
    };
    diagnostics?: {
      scope?: string | null;
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

const cacheLabels: Record<string, string> = {
  HIT: 'Cachetreffer',
  MISS: 'Kein Cachetreffer',
  BYPASS: 'Cache nicht verwendet',
  STALE_REJECTED: 'Veralteter Cacheeintrag verworfen',
};

function date(value: string | null): string {
  return value
    ? `${new Date(value).toLocaleString('de-DE', { timeZone: 'UTC' })} UTC`
    : 'Unbekannt';
}

function DiagnosticTime({ value }: { value?: string | null }) {
  if (!value) return <>Unbekannt</>;
  if (!/(?:Z|[+-]\d{2}:\d{2})$/i.test(value) || Number.isNaN(Date.parse(value))) {
    return <>{value} · Zeitbasis nicht belegt</>;
  }
  return <time dateTime={value}>{date(value)}</time>;
}

function evidence(value: boolean | null | undefined): string {
  return value === true ? 'Ja' : value === false ? 'Nein' : 'Nicht belegt';
}

function RefreshCacheDetails({ quotes }: { quotes?: RefreshCacheEvidence[] | null }) {
  return (
    <details className="mt-3 rounded-lg border border-slate-700 p-3">
      <summary className="cursor-pointer rounded font-medium text-slate-200 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-300">
        Cachebelege des letzten abgeschlossenen Laufs
      </summary>
      <p className="mt-2">
        Cacheangaben gehören zur jeweiligen gelieferten Kursantwort und ihrer Quellenidentität. Ein
        Cachetreffer belegt keinen neuen Providerkontakt und keine Wiederherstellung.
      </p>
      {!quotes ? (
        <p className="mt-2">Cachebelege wurden in dieser Statusantwort nicht mitgeliefert.</p>
      ) : quotes.length === 0 ? (
        <p className="mt-2">Keine Kursantworten für diesen abgeschlossenen Lauf geliefert.</p>
      ) : (
        <ul aria-label="Gelieferte Cachebelege" className="mt-2 space-y-3">
          {quotes.map((quote, index) => (
            <li
              key={`${quote.provider}:${quote.warrant_listing_id}:${quote.identity_key}:${index}`}
              className="min-w-0 border-l border-slate-600 pl-3"
            >
              <dl className="grid min-w-0 gap-2 sm:grid-cols-2">
                <div className="min-w-0">
                  <dt className="font-medium text-slate-200">Cachezustand</dt>
                  <dd>
                    {quote.cache_status
                      ? `${cacheLabels[quote.cache_status] ?? 'Cachezustand derzeit nicht einordenbar'} · ${quote.cache_status}`
                      : 'Nicht belegt'}
                  </dd>
                </div>
                <div className="min-w-0">
                  <dt className="font-medium text-slate-200">Provider</dt>
                  <dd>{quote.provider ?? 'Nicht belegt'}</dd>
                </div>
                <div className="min-w-0">
                  <dt className="font-medium text-slate-200">Notierung</dt>
                  <dd>{quote.warrant_listing_id ?? 'Nicht belegt'}</dd>
                </div>
                <div className="min-w-0">
                  <dt className="font-medium text-slate-200">Quellenidentität</dt>
                  <dd>{quote.identity_key ?? 'Nicht belegt'}</dd>
                </div>
                <div className="min-w-0">
                  <dt className="font-medium text-slate-200">Abrufzeit der Kursantwort</dt>
                  <dd>
                    <DiagnosticTime value={quote.retrieved_at} />
                  </dd>
                </div>
                <div className="min-w-0">
                  <dt className="font-medium text-slate-200">Abschluss dieses Quellenversuchs</dt>
                  <dd>
                    <DiagnosticTime value={quote.attempt_completed_at} />
                  </dd>
                </div>
              </dl>
            </li>
          ))}
        </ul>
      )}
    </details>
  );
}

function RefreshDiagnostics({
  reason,
  jobKey,
  checks,
  scope,
  completedAt,
  quotes,
}: {
  reason: string;
  jobKey: string;
  checks?: RefreshCheck[];
  scope?: string | null;
  completedAt?: string | null;
  quotes?: RefreshCacheEvidence[] | null;
}) {
  return (
    <details className="mt-2 min-w-0 text-sm text-slate-300 [overflow-wrap:anywhere]">
      <summary className="cursor-pointer rounded font-medium text-slate-200 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-300">
        Diagnose
        {checks &&
          checks.length > 0 &&
          ` · ${checks.length} ${checks.length === 1 ? 'Abrufnachweis' : 'Abrufnachweise'}`}
      </summary>
      <p className="mt-2">{reason}</p>
      <p>Auftragsidentität: {jobKey}</p>
      <p>Geltungsbereich: {scope ?? 'Nicht belegt'}</p>
      <p>
        Letzter abgeschlossener Schedulerlauf: <DiagnosticTime value={completedAt} />
      </p>
      <p className="mt-2">
        Die folgenden Belege beschreiben abgeschlossene Prüfungen. Providerkontakt, Antwort,
        verwendbarer Kurs und qualifizierter Erfolg sind getrennte Aussagen. Ein laufender Abruf hat
        noch kein neues Ergebnis; frühere Belege bleiben an ihre eigenen Zeiten gebunden.
      </p>
      <h3 className="mt-3 font-semibold text-slate-200">Abgeschlossene Diagnosebelege</h3>
      {!checks ? (
        <p className="mt-2">Diagnosebelege wurden in dieser Statusantwort nicht mitgeliefert.</p>
      ) : checks.length === 0 ? (
        <p className="mt-2">Keine abgeschlossenen Diagnosebelege in dieser Statusantwort.</p>
      ) : (
        <ul aria-label="Abgeschlossene Diagnosebelege" className="mt-3 space-y-3">
          {checks.map((check) => (
            <li
              key={`${check.kind}:${check.source}:${check.listing_id}:${check.identity_key ?? ''}`}
              className="min-w-0 rounded-lg border border-slate-700 p-3"
            >
              <h4 className="font-semibold text-slate-100">
                {check.kind === 'JOB' ? 'Auftrag' : (check.source ?? 'Quelle unbekannt')}
              </h4>
              <p className="mt-1">
                {check.observed_in_latest_run === true
                  ? 'Beleg aus dem letzten abgeschlossenen Lauf.'
                  : check.observed_in_latest_run === false
                    ? 'Historischer Beleg · In letzter Prüfung nicht erneut geprüft.'
                    : 'Zuordnung zum letzten abgeschlossenen Lauf nicht belegt.'}
              </p>
              {check.kind === 'SOURCE' && (
                <>
                  <p>Notierung: {check.listing_id ?? 'Nicht belegt'}</p>
                  <p>Quellenidentität: {check.identity_key ?? 'Nicht belegt'}</p>
                  <p>
                    Beginn dieses Quellenversuchs:{' '}
                    <DiagnosticTime value={check.attempt_started_at} />
                  </p>
                </>
              )}
              <p>
                Letzte Quellen- oder Auftragsprüfung:{' '}
                <DiagnosticTime value={check.last_checked_at} /> · Statuscode: {check.status}
              </p>
              <p>Diagnosekategorie: {check.category ?? 'Nicht geliefert'}</p>
              {check.reason && <p>Diagnosecode: {check.reason}</p>}
              {check.kind === 'SOURCE' && (
                <>
                  <h5 className="mt-3 font-semibold text-slate-200">Providerantwort und Kurs</h5>
                  <dl className="mt-2 grid min-w-0 gap-3 sm:grid-cols-2">
                    <div className="min-w-0">
                      <dt className="text-slate-400">Providerkontakt</dt>
                      <dd>Provider technisch erreichbar: {evidence(check.provider_reachable)}</dd>
                    </div>
                    <div className="min-w-0">
                      <dt className="text-slate-400">Antwortprüfung</dt>
                      <dd>Antwort gültig: {evidence(check.response_valid)}</dd>
                    </div>
                    <div className="min-w-0">
                      <dt className="text-slate-400">Fachliche Verwendbarkeit</dt>
                      <dd>Kurs verwendbar: {evidence(check.quote_usable)}</dd>
                    </div>
                    <div className="min-w-0">
                      <dt className="text-slate-400">Erfolgsqualifikation des Backends</dt>
                      <dd>
                        Qualifizierter Erfolg dieser Prüfung: {evidence(check.qualified_success)}
                      </dd>
                    </div>
                    <div className="min-w-0">
                      <dt className="text-slate-400">Kursbewertung dieser Prüfung</dt>
                      <dd>
                        <p>
                          {check.quote_status
                            ? (quoteLabels[check.quote_status] ??
                              'Kursstatus derzeit nicht einordenbar')
                            : 'Kursbewertung nicht mitgeliefert'}
                        </p>
                        <p>Kursstatuscode: {check.quote_status ?? 'Nicht geliefert'}</p>
                      </dd>
                    </div>
                    <div className="min-w-0">
                      <dt className="text-slate-400">Retention</dt>
                      <dd>Gespeicherter Ersatzkurs: {evidence(check.retained_quote)}</dd>
                    </div>
                  </dl>
                  {check.retained_quote && (
                    <p className="mt-2 text-amber-200">
                      Gespeicherter Ersatzkurs vorhanden. Kein Nachweis eines aktuellen
                      Providererfolgs.
                    </p>
                  )}
                  <p className="mt-2">
                    Kurszeit: <DiagnosticTime value={check.quote_observed_at} /> · Abrufzeit des
                    Kurses: <DiagnosticTime value={check.quote_retrieved_at} />
                  </p>
                </>
              )}
              <h5 className="mt-3 font-semibold text-slate-200">
                Fehlerfolge und frühere Ergebnisse
              </h5>
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
                    Seit: <DiagnosticTime value={check.first_failure_at} /> · Zuletzt festgestellt:{' '}
                    <DiagnosticTime value={check.last_failure_at} />
                  </p>
                </>
              ) : check.recovered_at ? (
                <p>
                  Historischer Wiederherstellungsbeleg ·{' '}
                  {check.kind === 'SOURCE'
                    ? 'Kursversorgung wiederhergestellt'
                    : 'Auftrag wieder abgeschlossen'}
                  : <DiagnosticTime value={check.recovered_at} />
                </p>
              ) : (
                <p>
                  0 Prüfungen in Folge mit Befund. Daraus folgt kein Nachweis der
                  Providererreichbarkeit.
                </p>
              )}
              {check.consecutive_failures > 0 && check.recovered_at && (
                <p>
                  Früherer Wiederherstellungsbeleg: <DiagnosticTime value={check.recovered_at} />.{' '}
                  Die gemeldete Fehlerfolge bleibt bestehen.
                </p>
              )}
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
                  : 'Letzter erfolgreich abgeschlossener Auftrag'}
                : <DiagnosticTime value={check.last_success_at} />
              </p>
              {check.last_failure_at && (
                <p>
                  Letzter fehlgeschlagener Abruf: <DiagnosticTime value={check.last_failure_at} />
                </p>
              )}
              {check.last_failure_reason && check.last_failure_reason !== check.reason && (
                <p>Vorheriger Befund: {check.last_failure_reason}</p>
              )}
              {check.last_failure_category && (
                <p>Letzte Fehlerkategorie: {check.last_failure_category}</p>
              )}
            </li>
          ))}
        </ul>
      )}
      <RefreshCacheDetails quotes={quotes} />
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
    <details className="mb-6 min-w-0 rounded-xl border border-slate-800 bg-slate-900/60 p-4 [overflow-wrap:anywhere]">
      <summary className="cursor-pointer rounded text-sm font-semibold text-slate-200 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-300">
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
        className="mt-3 rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-200 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-300"
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
          {value.jobs.some((job) => job.diagnostics?.scope === 'PROCESS_LOCAL') && (
            <p className="mt-2 text-xs text-slate-400">
              Abrufdiagnosen gelten nur für diese Backend-Laufzeit und werden bei einem Neustart
              zurückgesetzt. Sie belegen keinen dauerhaften Verfügbarkeitsverlauf. Das Kursalter
              steht separat unter „Kursquellen im Depot“.
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
              <li key={job.job} className="min-w-0 py-2">
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
                      · Nächste Prüfung frühestens <DiagnosticTime value={job.next_run_at} />
                    </>
                  )}
                </p>
                {job.execution?.running && (
                  <p className="text-xs text-slate-400">
                    Aktueller Abruf · Start: <DiagnosticTime value={job.execution.started_at} />
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
                <RefreshDiagnostics
                  reason={job.reason}
                  jobKey={job.job}
                  checks={job.diagnostics?.checks}
                  scope={job.diagnostics?.scope}
                  completedAt={job.checked_at}
                  quotes={job.quotes}
                />
              </li>
            ))}
          </ul>
        </div>
      )}
    </details>
  );
}
