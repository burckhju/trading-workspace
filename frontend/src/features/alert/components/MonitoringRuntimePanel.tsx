import { useEffect, useState } from 'react';

import { alertApiClient } from '../services/client';
import type { MonitoringRuntimeStatusResponse } from '../types/api';

function runtimeLabel(value: MonitoringRuntimeStatusResponse): string {
  if (!value.enabled) return 'Automatische Prüfung deaktiviert';
  if (!value.running) return 'Automatische Prüfung nicht gestartet oder beendet';
  if (value.cycle_running) return 'Prüfdurchlauf läuft';
  if (value.last_error) return 'Letzter Prüfdurchlauf fehlgeschlagen';
  if (!value.last_result) return 'Erster Prüfdurchlauf steht aus';
  if (
    [
      'subject_errors',
      'missing_market_data',
      'stale_market_data',
      'market_data_errors',
      'position_errors',
    ].some((key) => (value.last_result?.[key] ?? 0) > 0)
  ) {
    return 'Prüfung aktiv · Daten- oder Regelfehler im letzten Durchlauf';
  }
  return 'Automatische Prüfung aktiv';
}

const counts: [string, string][] = [
  ['positions_seen', 'Positionen erfasst'],
  ['positions_checked', 'Positionen mit Kursdaten geprüft'],
  ['rules_evaluated', 'Regeln ausgewertet'],
  ['subject_errors', 'Zuordnung oder Regeln fehlen'],
  ['missing_market_data', 'Kursdaten fehlen'],
  ['stale_market_data', 'Kursdaten zu alt'],
  ['market_data_errors', 'Kursdatenfehler'],
  ['position_errors', 'Fehler bei der Regelauswertung'],
  ['alerts_created', 'Neue Meldungen'],
  ['notification_failures', 'Versandfehler'],
];

export function MonitoringRuntimePanel() {
  const [value, setValue] = useState<MonitoringRuntimeStatusResponse | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    alertApiClient
      .monitoringRuntime(controller.signal)
      .then((result) => {
        if (!controller.signal.aborted) setValue(result);
      })
      .catch(() => {
        if (!controller.signal.aborted) setFailed(true);
      });
    return () => controller.abort();
  }, []);

  return (
    <div
      className="mt-4 rounded-lg border border-slate-800 p-4"
      aria-label="Automatische Stop-/Ziel-Prüfung"
    >
      <p className="text-xs uppercase tracking-wide text-slate-500">
        Automatische Stop-/Ziel-Prüfung
      </p>
      <p className="mt-1 font-medium">
        {value
          ? runtimeLabel(value)
          : failed
            ? 'Laufstatus nicht verfügbar'
            : 'Laufstatus wird geladen…'}
      </p>
      <p className="mt-2 text-sm text-slate-400">
        Stop und Ziel werden anhand abgeschlossener Tagesdaten des Basiswerts geprüft. Der
        Optionsscheinkurs dient separat der Produktbewertung.
      </p>
      {value && (
        <>
          <p className="mt-2 text-xs text-slate-400">
            Prüfintervall: {value.interval_seconds} Sekunden · Tagesdaten, keine Intraday-Prüfung
          </p>
          {value.last_cycle_started_at && (
            <p className="mt-2 text-xs text-slate-400">
              Letzter Start: {new Date(value.last_cycle_started_at).toLocaleString('de-DE')}
            </p>
          )}
          {value.last_cycle_completed_at && (
            <p className="mt-2 text-xs text-slate-400">
              Letzter abgeschlossener Durchlauf:{' '}
              {new Date(value.last_cycle_completed_at).toLocaleString('de-DE')}
            </p>
          )}
          {value.last_error && (
            <p className="mt-2 text-sm text-amber-300">
              Ein Durchlauf ist fehlgeschlagen. Die Zähler zeigen, soweit vorhanden, den vorherigen
              abgeschlossenen Durchlauf.
            </p>
          )}
          {value.last_result && (
            <p className="mt-2 text-sm text-slate-400">
              Letzter abgeschlossener Durchlauf: {value.last_result.positions_checked} von{' '}
              {value.last_result.positions_seen} Positionen mit Kursdaten geprüft;{' '}
              {value.last_result.rules_evaluated} Regeln ausgewertet.
            </p>
          )}
          {value.last_result && (
            <details className="mt-3 text-xs text-slate-400">
              <summary className="cursor-pointer">
                Ergebnis des letzten abgeschlossenen Durchlaufs anzeigen
              </summary>
              <p className="mt-2">
                Alle Positionen dieses Backend-Prozesses; Stand seit dem letzten Neustart.
              </p>
              <dl className="mt-2 grid gap-2 sm:grid-cols-2">
                {counts.map(([key, label]) => (
                  <div key={key}>
                    <dt>{label}</dt>
                    <dd>{value.last_result?.[key] ?? '—'}</dd>
                  </div>
                ))}
              </dl>
            </details>
          )}
        </>
      )}
    </div>
  );
}
