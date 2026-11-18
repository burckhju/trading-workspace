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
      'blocked_rules',
      'missing_market_data',
      'stale_market_data',
      'market_data_errors',
      'position_errors',
      'review_data_problems',
      'review_position_errors',
      'deadline_data_problems',
      'deadline_position_errors',
    ].some((key) => (value.last_result?.[key] ?? 0) > 0)
  ) {
    return 'Prüfung aktiv · Daten- oder Regelfehler im letzten Durchlauf';
  }
  return 'Automatische Prüfung aktiv';
}

const reviewCounts: [string, string][] = [
  ['review_positions_evaluated', 'Positionen ausgewertet'],
  ['review_alerts_created', 'Hinweise erstellt'],
  ['review_data_problems', 'Datenprobleme'],
  ['review_position_errors', 'Fehler bei der Auswertung'],
];

const deadlineCounts: [string, string][] = [
  ['deadline_positions_evaluated', 'Positionen auf Produkttermine geprüft'],
  ['deadline_alerts_created', 'Produkttermin-Hinweise erstellt'],
  ['deadline_data_problems', 'Produkt- oder Kalenderprobleme'],
  ['deadline_position_errors', 'Fehler bei der Terminprüfung'],
];

function deadlineLabel(value: MonitoringRuntimeStatusResponse): string {
  if (value.review_rule_version !== 'indicative-entry-review-v2')
    return 'Produkttermin-Teilumfang nicht belegt';
  if (!value.enabled || !value.running)
    return 'Produkttermin-Teilumfang gewählt · Hintergrundprüfung nicht aktiv';
  if (value.last_error) return 'Produkttermin-Prüfung · letzter Durchlauf fehlgeschlagen';
  if (!value.last_cycle_completed_at || !value.last_result)
    return 'Produkttermin-Prüfung · erster Abschluss noch nicht belegt';
  if (
    deadlineCounts.some(
      ([key]) =>
        !Number.isInteger(value.last_result?.[key]) || (value.last_result?.[key] ?? -1) < 0,
    )
  )
    return 'Produkttermin-Prüfergebnis nicht verfügbar';
  if (
    value.last_result.deadline_data_problems > 0 ||
    value.last_result.deadline_position_errors > 0
  )
    return 'Produkttermin-Prüfung mit Daten- oder Auswertungsproblemen';
  if (value.last_result.deadline_positions_evaluated === 0)
    return 'Produkttermin-Prüfung · keine Position ausgewertet';
  return 'Letzter Produkttermin-Prüfdurchlauf abgeschlossen';
}

function reviewLabel(value: MonitoringRuntimeStatusResponse): string {
  if (
    value.review_scope !== 'DISABLED' &&
    value.review_scope !== 'INDICATIVE_ENTRY_V1' &&
    value.review_scope !== 'INDICATIVE_ENTRY_V2'
  ) {
    return 'Aktivierung dieses Teilumfangs nicht belegt';
  }
  if (value.review_scope === 'DISABLED') return 'Indikative Beobachtung deaktiviert';
  const expectedVersion =
    value.review_scope === 'INDICATIVE_ENTRY_V2'
      ? 'indicative-entry-review-v2'
      : 'indicative-entry-review-v1';
  if (value.review_rule_version !== expectedVersion) {
    return 'Teilumfang gewählt · Regelversion nicht belegt';
  }
  if (!value.enabled) return 'Teilumfang gewählt · Hintergrundprüfung deaktiviert';
  if (!value.running) return 'Teilumfang gewählt · Hintergrundprüfung nicht gestartet';
  if (value.last_error) return 'Teilumfang eingeschaltet · letzter Prüfdurchlauf fehlgeschlagen';
  if (!value.last_cycle_completed_at || !value.last_result) {
    return 'Teilumfang eingeschaltet · erster Abschluss noch nicht belegt';
  }
  if (
    reviewCounts.some(
      ([key]) =>
        !Number.isInteger(value.last_result?.[key]) || (value.last_result?.[key] ?? -1) < 0,
    )
  ) {
    return 'Teilumfang eingeschaltet · Prüfergebnis nicht verfügbar';
  }
  if (value.last_result.review_data_problems > 0 || value.last_result.review_position_errors > 0) {
    return 'Teilumfang eingeschaltet · Daten- oder Auswertungsprobleme';
  }
  if (value.last_result.review_positions_evaluated === 0) {
    return 'Teilumfang eingeschaltet · keine Position ausgewertet';
  }
  return 'Letzter indikativer Prüfdurchlauf abgeschlossen';
}

const counts: [string, string][] = [
  ['positions_seen', 'Positionen erfasst'],
  ['positions_checked', 'Positionen mit Kursdaten geprüft'],
  ['rules_evaluated', 'Regeln ausgewertet'],
  ['blocked_rules', 'Regeln blockiert: Kursbezug oder Zuordnung prüfen'],
  ['alerts_invalidated', 'Historische Meldungen ungültig gesetzt'],
  ['subject_errors', 'Zuordnung oder Regeln fehlen'],
  ['missing_market_data', 'Kursdaten fehlen'],
  ['stale_market_data', 'Kursdaten zu alt'],
  ['market_data_errors', 'Kursdatenfehler'],
  ['position_errors', 'Fehler bei der Regelauswertung'],
  ['alerts_created', 'Neue Meldungen'],
  ['notification_failures', 'Versandfehler'],
];

export function MonitoringRuntimePanel({ tradeId }: { tradeId?: string }) {
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
    <div className="mt-4 rounded-lg border border-slate-800 p-4">
      <p className="text-xs uppercase tracking-wide text-slate-500">
        Automatische Positionsprüfung
      </p>
      <p className="mt-1 font-medium">
        {value
          ? runtimeLabel(value)
          : failed
            ? 'Laufstatus nicht verfügbar'
            : 'Laufstatus wird geladen…'}
      </p>
      <p className="mt-2 text-sm text-slate-400">
        Stop-/Ziel-Regeln verwenden ihren bestätigten Instrument- und Währungsbezug.
        Basiswert-Regeln verwenden abgeschlossene Tagesdaten; Optionsschein-Regeln den ausgewiesenen
        Produktkurs. Regeln ohne bestätigten Kursbezug bleiben blockiert.
      </p>
      {value && (
        <>
          <section
            className="mt-3 rounded border border-slate-700 p-3 text-sm"
            aria-label="Indikative Einstandsbeobachtung"
          >
            <p className="font-medium">Indikative Einstandsbeobachtung</p>
            <p className="mt-1">{reviewLabel(value)}</p>
            <p className="mt-2 text-xs text-slate-400">
              Regelumfang: {value.review_scope ?? 'nicht belegt'}
            </p>
            <p className="mt-2 text-xs text-slate-400">
              Regelversion: {value.review_rule_version ?? 'nicht belegt'}
            </p>
            {value.review_scope === 'INDICATIVE_ENTRY_V2' && (
              <p className="mt-2 text-xs text-amber-200">
                Erweiterter indikativer Teilumfang: verzögerte Kurse, unbekanntes Kursalter und
                angenommene historische Maßstabskontinuität werden je Position ausgewiesen. Bekannte
                Widersprüche sperren den Vergleich. Der aktuelle Instrumentmarktstatus ist damit
                nicht bestätigt.
              </p>
            )}
            <p className="mt-1 text-xs text-slate-400">
              Kursvergleich, 20-Sitzungen-Prüfhinweise und Datenprobleme sind getrennte Hinweise.
              Dieser Teilumfang aktiviert keine qualifizierte B04/B57-Überwachung und keine
              vollständige Hebeltrader-Baseline.
            </p>
            <p className="mt-2 text-xs text-slate-400">
              {value.review_notifications_enabled === false
                ? 'Hinweise im Arbeitsbereich · externe Zustellung dieses Teilumfangs ausgeschaltet.'
                : value.review_notifications_enabled === true
                  ? 'Externe Zustellung dieses Teilumfangs konfiguriert; tatsächlichen Versand am jeweiligen Hinweis prüfen.'
                  : 'Konfiguration der externen Zustellung dieses Teilumfangs nicht belegt.'}
            </p>
            {(value.review_scope === 'INDICATIVE_ENTRY_V1' ||
              value.review_scope === 'INDICATIVE_ENTRY_V2') &&
              value.last_cycle_completed_at &&
              value.last_result && (
                <dl className="mt-3 grid gap-2 sm:grid-cols-2">
                  {reviewCounts.map(([key, label]) => (
                    <div key={key}>
                      <dt className="text-slate-500">
                        {label} · letzter abgeschlossener Durchlauf
                      </dt>
                      <dd>{value.last_result?.[key] ?? 'nicht belegt'}</dd>
                    </div>
                  ))}
                </dl>
              )}
          </section>
          {value.review_scope === 'INDICATIVE_ENTRY_V2' && (
            <section
              className="mt-3 rounded border border-slate-700 p-3 text-sm"
              aria-label="Produkttermin-Erinnerungen"
            >
              <p className="font-medium">Produkttermin-Erinnerungen</p>
              <p className="mt-1">{deadlineLabel(value)}</p>
              <p className="mt-2 text-xs text-slate-400">
                Kalendererinnerungen aus vorhandenen Produkt- und Handelsplatzbelegen; unabhängig
                von der aktuellen Geldkursverfügbarkeit. Tagesgenaue Belege bleiben tagesgenau.
                Produktbezogene letzte Handelsuhrzeit und vollständige B05-Qualifikation bleiben
                offen.
              </p>
              {value.last_cycle_completed_at && value.last_result && (
                <dl className="mt-3 grid gap-2 sm:grid-cols-2">
                  {deadlineCounts.map(([key, label]) => (
                    <div key={key}>
                      <dt className="text-slate-500">
                        {label} · letzter abgeschlossener Durchlauf
                      </dt>
                      <dd>{value.last_result?.[key] ?? 'nicht belegt'}</dd>
                    </div>
                  ))}
                </dl>
              )}
            </section>
          )}
          <p className="mt-2 text-xs text-slate-400">
            Prüfintervall: {value.interval_seconds} Sekunden · Kursart und Aktualität je Regel
            beachten
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
          {tradeId &&
            value.last_rule_checks
              ?.filter((check) => check.trade_id === tradeId)
              .map((check) => (
                <div
                  key={check.rule_key}
                  className="mt-3 rounded border border-slate-700 p-3 text-sm"
                >
                  <p>
                    {check.rule_key === 'CURRENT_STOP' ? 'Stop-Prüfung' : 'Ziel-Prüfung'} ·{' '}
                    {check.basis === 'WARRANT'
                      ? 'Optionsschein'
                      : check.basis === 'UNDERLYING'
                        ? 'Basiswert'
                        : 'Kursbezug ungeklärt'}
                  </p>
                  <p>
                    Schwelle: {check.threshold} {check.currency} · Beobachtet:{' '}
                    {check.observed_value ?? '—'} · {check.status}
                  </p>
                  <p className="text-xs text-slate-400">
                    {check.reason} · {check.provider ?? 'Quelle nicht verfügbar'} ·{' '}
                    {check.price_type ?? '—'}
                  </p>
                  {check.warning && (
                    <p className="text-xs text-amber-300">Indikative Prüfung: {check.warning}</p>
                  )}
                </div>
              ))}
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
