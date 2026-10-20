import { useState } from 'react';

import { environment } from '../../../services/environment';
import { requestJson } from '../../market/services/http';
import { QuoteCoveragePanel } from './QuoteCoveragePanel';

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
    source_selection?: {
      positions_checked: number;
      decisions_changed: number;
      statuses: Record<string, number>;
    } | null;
  }>;
};

function statusLabel(status: string): string {
  if (status === 'NEEDS_MASTER_DATA') return 'Stammdaten ergänzen oder prüfen';
  if (status === 'PENDING') return 'Erster Abruf steht aus';
  if (status === 'DEFERRED') return 'Abruflimit erreicht · Wiederholung eingeplant';
  if (status === 'AVAILABLE') return 'Erfolgreich';
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
            verzögern.
          </p>
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
              {(['ISSUER_DISCOVERY', 'ISSUER_QUOTES', 'WARRANTS', 'UNDERLYINGS'] as const).map(
                (lane) => {
                  const progress = value.lanes?.[lane];
                  if (!progress) return null;
                  return (
                    <li key={lane}>
                      {lane === 'ISSUER_DISCOVERY'
                        ? 'Neue Emittentenprodukte'
                        : lane === 'ISSUER_QUOTES'
                          ? 'Emittentenkurse'
                          : lane === 'WARRANTS'
                            ? 'Optionsscheine'
                            : 'Basiswerte'}
                      : {progress.running ? 'Abruf läuft' : 'Wartet auf nächste Prüfung'} ·{' '}
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
                              · längster Rückstand {Math.ceil(
                                progress.max_overdue_seconds / 60,
                              )}{' '}
                              Min.
                            </>
                          )}
                        </>
                      )}
                    </li>
                  );
                },
              )}
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
                  {Object.values(value.current_jobs ?? {}).includes(job.job) ||
                  value.current_job === job.job
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
                <details className="mt-1 text-xs text-slate-400">
                  <summary>Diagnose</summary>
                  {job.reason}
                </details>
              </li>
            ))}
          </ul>
        </div>
      )}
    </details>
  );
}
