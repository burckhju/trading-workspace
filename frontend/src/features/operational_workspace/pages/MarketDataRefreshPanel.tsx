import { useState } from 'react';

import { environment } from '../../../services/environment';
import { requestJson } from '../../market/services/http';

type RefreshStatus = {
  enabled: boolean;
  running: boolean;
  leader: boolean;
  last_error: string | null;
  settings: {
    warrants_interval_seconds: number;
    underlyings_interval_seconds: number;
    discovery_interval_seconds: number;
  };
  jobs: Array<{
    job: string;
    name: string;
    isin: string | null;
    status: string;
    reason: string;
    next_run_at: string;
  }>;
};

function statusLabel(status: string): string {
  if (status === 'AVAILABLE') return 'Erfolgreich';
  if (status === 'MISSING') return 'Keine Kursdaten';
  if (status === 'BLOCKED') return 'Zuordnung oder Zugang fehlt';
  return 'Abruf prüfen';
}

function taskLabel(job: string): string {
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
        Verfügbare Kurse behalten ihren ursprünglichen Kurszeitpunkt.
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
          {value.last_error && (
            <p className="mt-2 text-amber-300">Letzte Prüfung fehlgeschlagen: {value.last_error}</p>
          )}
          <ul className="mt-3 divide-y divide-slate-800">
            {value.jobs.map((job) => (
              <li key={job.job} className="py-2">
                <p>
                  {job.name} · {job.isin ?? 'ISIN fehlt'} · {taskLabel(job.job)}
                </p>
                <p>
                  {statusLabel(job.status)} · Nächste Prüfung frühestens{' '}
                  {new Date(job.next_run_at).toLocaleString('de-DE')}
                </p>
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
