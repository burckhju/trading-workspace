import { useEffect, useState } from 'react';

import { riskPercent } from '../services/riskLabels';
import { alertTypeLabel } from '../services/alertLabels';
import { alertApiClient } from '../services/client';
import type {
  AlertResponse,
  NotificationResponse,
  PositionMonitoringHealthResponse,
} from '../types/api';
import { MonitoringRuntimePanel } from './MonitoringRuntimePanel';

function formatDateTime(value: string | null): string {
  return value ? new Date(value).toLocaleString('de-DE') : '—';
}

function formatDate(value: string | null): string {
  return value ? new Date(`${value}T00:00:00`).toLocaleDateString('de-DE') : '—';
}

function formatNumber(value: string | null): string {
  return value === null
    ? '—'
    : new Intl.NumberFormat('de-DE', { maximumFractionDigits: 10 }).format(Number(value));
}

function isEntryObservation(alert: AlertResponse): boolean {
  return (
    alert.alert_type === 'INDICATIVE_ENTRY_LOSS' ||
    alert.alert_type === 'POSITION_REVIEW_DUE' ||
    alert.alert_type === 'POSITION_DATA_UNAVAILABLE'
  );
}

function hasPriceTrigger(alert: AlertResponse): boolean {
  return (
    alert.alert_type !== 'POSITION_REVIEW_DUE' && alert.alert_type !== 'POSITION_DATA_UNAVAILABLE'
  );
}

function alertTriggerLabel(alert: AlertResponse): string {
  if (alert.alert_type === 'POSITION_REVIEW_DUE') {
    return 'Anlass: abgeschlossene Basiswertsitzungen';
  }
  if (alert.alert_type === 'POSITION_DATA_UNAVAILABLE') {
    return 'Datenlage: Einstandsbeobachtung nicht beurteilbar';
  }
  return alert.price_context
    ? `Auslöser: ${alert.price_context.basis === 'WARRANT' ? 'Optionsschein' : 'Basiswert'} · ${alert.price_context.price_type ?? 'Kurs'} · ${alert.price_context.currency ?? '—'}`
    : 'Kursbezug ungeklärt · historische Meldung nicht belastbar';
}

function alertTitle(alert: AlertResponse): string {
  const title =
    alert.alert_type === 'TARGET_REACHED' ? 'Target erreicht' : alertTypeLabel(alert.alert_type);
  return !isEntryObservation(alert) && alert.price_context?.evaluation_mode === 'INDICATIVE_ISSUER'
    ? `${title} (indikative Prüfung)`
    : title;
}

const reviewSuppressionCodes = new Set([
  'REVIEW_POSITION_CLOSED',
  'REVIEW_ALERT_RESOLVED',
  'REVIEW_ALERT_INVALIDATED',
  'REVIEW_TRADE_CANCELLED',
  'REVIEW_TRADE_MISSING',
]);

function notificationLabel(notification: NotificationResponse): string {
  if (notification.status === 'DELIVERED') return `${notification.channel}: zugestellt`;
  const errorCode = notification.last_delivery?.error_code;
  if (errorCode?.startsWith('B04_') || reviewSuppressionCodes.has(errorCode ?? '')) {
    return `${notification.channel}: Versand unterdrückt · ${notification.last_delivery?.error_message ?? 'Hinweis ist nicht mehr zustellbar.'}`;
  }
  if (notification.status === 'FAILED') return `${notification.channel}: fehlgeschlagen`;
  if (notification.last_delivery?.status === 'IN_PROGRESS') {
    return `${notification.channel}: Versand läuft`;
  }
  return `${notification.channel}: ausstehend`;
}

function healthLabel(health: PositionMonitoringHealthResponse): string {
  if (health.status === 'OK') return 'Daten aktuell';
  if (health.status === 'STALE') return 'Daten veraltet';
  if (health.status === 'MISSING') return 'Daten fehlen';
  return 'Datenproblem';
}

function healthExplanation(health: PositionMonitoringHealthResponse): string {
  if (health.status === 'OK') {
    return 'Die Basiswertdaten sind aktuell genug. Eine Regel wird nur mit ausdrücklich bestätigtem Kursbezug geprüft.';
  }
  if (health.status === 'STALE') {
    return 'Die abgeschlossenen Tagesdaten des Basiswerts sind zu alt. Optionsschein-Regeln verwenden ihre eigene Kursquelle.';
  }
  if (health.status === 'MISSING') {
    return 'Abgeschlossene Tagesdaten des Basiswerts fehlen. Optionsschein-Regeln verwenden ihre eigene Kursquelle.';
  }
  return 'Die Monitoring-Daten konnten nicht verlässlich ausgewertet werden. Es wird kein scheinbar normaler Stop-/Target-Zustand angenommen.';
}

export function TradeAlertsPanel({ tradeId }: { tradeId: string }) {
  const [alerts, setAlerts] = useState<AlertResponse[]>([]);
  const [health, setHealth] = useState<PositionMonitoringHealthResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    setHealth(null);

    const alertsRequest = alertApiClient.forTrade(tradeId, controller.signal).then(setAlerts);
    const healthRequest = alertApiClient
      .monitoringHealth(tradeId, controller.signal)
      .then(setHealth)
      .catch(() => {
        if (!controller.signal.aborted) setHealth(null);
      });

    Promise.all([alertsRequest, healthRequest])
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(
            reason instanceof Error ? reason.message : 'Alerts konnten nicht geladen werden.',
          );
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });

    return () => controller.abort();
  }, [tradeId]);

  const openCount = alerts.filter((alert) => alert.status === 'OPEN').length;

  return (
    <>
      <section
        className="rounded-xl border border-slate-800 p-5"
        aria-labelledby="trade-alerts-title"
      >
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-xs uppercase tracking-wide text-slate-500">Monitoring</p>
            <h2 id="trade-alerts-title" className="mt-1 text-lg font-semibold">
              Positions-Alerts
            </h2>
            <p className="mt-1 text-xs text-slate-500">
              Underlying-Datenzustand, fachliche Alerts und Notification-Delivery werden getrennt
              dargestellt.
            </p>
          </div>
          <span className="rounded-full border border-slate-700 px-3 py-1 text-xs">
            {openCount} offen
          </span>
        </div>

        <MonitoringRuntimePanel key={tradeId} tradeId={tradeId} />

        {health && (
          <div className="mt-4 rounded-lg border border-slate-800 p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-500">
                  Basiswert · Tagesdaten
                </p>
                <p className="mt-1 font-medium">{healthLabel(health)}</p>
              </div>
              <span className="rounded-full border border-slate-700 px-2.5 py-1 text-xs">
                {health.status}
              </span>
            </div>
            <p className="mt-2 text-sm text-slate-400">{healthExplanation(health)}</p>
            {health.basis && (
              <p className="mt-2 text-sm">
                {health.basis.name} · {health.basis.isin ?? 'ISIN nicht hinterlegt'} ·{' '}
                {health.basis.venue_mic} · {health.basis.currency}
              </p>
            )}
            {health.daily_price && (
              <>
                <dl className="mt-3 grid gap-3 text-sm sm:grid-cols-3">
                  {(
                    [
                      ['Schlusskurs', health.daily_price.close],
                      ['Tagestief · Stop-Prüfung', health.daily_price.low],
                      ['Tageshoch · Ziel-Prüfung', health.daily_price.high],
                    ] as const
                  ).map(([label, price]) => (
                    <div key={label}>
                      <dt className="text-slate-500">{label}</dt>
                      <dd className="mt-1">
                        {formatNumber(price)} {health.daily_price?.currency}
                      </dd>
                    </div>
                  ))}
                </dl>
                <p className="mt-2 text-xs text-slate-400">
                  Quelle: {health.daily_price.provider} · {health.daily_price.provider_symbol}
                </p>
                <p className="mt-2 text-xs text-slate-400">
                  Quellenzeitpunkt: {formatDateTime(health.daily_price.source_updated_at)} ·
                  Abgerufen: {formatDateTime(health.daily_price.retrieved_at)}
                </p>
              </>
            )}
            <dl className="mt-3 grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
              <div>
                <dt className="text-slate-500">Underlying</dt>
                <dd className="mt-1">{health.symbol ?? '—'}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Handelstag</dt>
                <dd className="mt-1">{formatDate(health.trading_date)}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Datenzeitpunkt</dt>
                <dd className="mt-1">{formatDateTime(health.market_data_observed_at)}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Alter</dt>
                <dd className="mt-1">
                  {health.age_days === null ? '—' : `${health.age_days} Tag(e)`}
                </dd>
              </div>
            </dl>
            {health.basis && (
              <details className="mt-3 text-xs text-slate-500">
                <summary className="cursor-pointer">Verwendetes Basiswert-Listing anzeigen</summary>
                <p className="mt-2 break-all">{health.basis.listing_id}</p>
              </details>
            )}
            {health.status !== 'OK' && (
              <details className="mt-3 text-xs text-slate-500">
                <summary className="cursor-pointer">Technischen Grund anzeigen</summary>
                <p className="mt-2 break-all">{health.reason}</p>
              </details>
            )}
          </div>
        )}

        {loading && <p className="mt-4 text-sm text-slate-400">Alerts werden geladen…</p>}
        {error && (
          <p role="alert" className="mt-4 rounded-lg border border-slate-700 p-3 text-sm">
            {error}
          </p>
        )}
        {!loading && !error && alerts.length === 0 && (
          <p className="mt-4 text-sm text-slate-400">
            Für diesen Trade liegen noch keine Alerts vor.
          </p>
        )}

        {!loading && !error && alerts.length > 0 && (
          <ol className="mt-4 space-y-3">
            {alerts.map((alert) => (
              <li key={alert.id} className="rounded-lg border border-slate-800 p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="font-medium">{alertTitle(alert)}</p>
                    <p className="mt-1 text-xs text-slate-400">{alertTriggerLabel(alert)}</p>
                    <p className="mt-1 text-sm text-slate-400">{alert.reason}</p>
                  </div>
                  <span className="rounded-full border border-slate-700 px-2.5 py-1 text-xs">
                    {alert.status === 'INVALIDATED' ? 'Ungültig' : alert.status}
                  </span>
                </div>

                {alert.invalidation_reason && (
                  <p className="mt-2 text-sm text-amber-300">
                    {alert.alert_type === 'HEBELTRADER_B04_LOSS'
                      ? 'B04-Verlusthinweis durch neue Bewertung ungültig. Ursprüngliche Werte bleiben zur Nachvollziehbarkeit erhalten.'
                      : isEntryObservation(alert)
                        ? 'Hinweis durch eine neue Bewertung ungültig. Ursprüngliche Angaben bleiben zur Nachvollziehbarkeit erhalten.'
                        : 'Meldung wegen ungeklärtem Kursbezug ungültig. Ursprüngliche Werte bleiben zur Nachvollziehbarkeit erhalten.'}
                  </p>
                )}
                {alert.alert_type === 'HEBELTRADER_B04_LOSS' && (
                  <div className="mt-2 text-sm text-slate-400">
                    <p>Regel: B04/B57 · {alert.price_context?.rule_version ?? 'nicht belegt'}</p>
                    <p>
                      Restmenge bei Auslösung: {alert.price_context?.remaining_quantity ?? '—'} ·
                      Abgeschlossene Basiswertsitzungen zur Geldkurszeit:{' '}
                      {alert.price_context?.completed_sessions_at_bid ?? '—'}
                    </p>
                    <p>
                      Verlustepisode zur Prüfung. Ausschließlich ein Hinweis; keine Orderfreigabe
                      und keine automatische Stop- oder Zieländerung.
                    </p>
                  </div>
                )}
                {isEntryObservation(alert) && (
                  <div className="mt-2 text-sm text-slate-400">
                    <p>
                      Teilumfang: Indikative Einstandsbeobachtung ·{' '}
                      {alert.price_context?.rule_version ?? 'Version nicht belegt'}
                    </p>
                    <p className="mt-1">
                      {alert.alert_type === 'INDICATIVE_ENTRY_LOSS'
                        ? 'Indikativer Vergleich mit dem persönlichen Bruttoeinstand. B58-Qualifikation nicht belegt; keine B04/B57-Verlustepisode.'
                        : alert.alert_type === 'POSITION_REVIEW_DUE'
                          ? 'Kalenderbasierter Prüfhinweis. Die abgeschlossenen Sitzungen allein belegen keinen Verlust; keine B04/B57-Verlustepisode.'
                          : 'Die Einstandsbeobachtung ist wegen fehlender oder ungeeigneter Daten nicht auswertbar. Ein bestehender Verlusthinweis bleibt davon getrennt.'}
                    </p>
                    {alert.alert_type === 'POSITION_REVIEW_DUE' ? (
                      <p className="mt-1">
                        Abgeschlossene Basiswertsitzungen zum Prüfzeitpunkt:{' '}
                        {alert.price_context?.review_completed_sessions ?? 'nicht belegt'} · Stand:{' '}
                        {alert.price_context?.review_session_count_at ?? 'nicht belegt'}
                      </p>
                    ) : (
                      <p className="mt-1">
                        Abgeschlossene Basiswertsitzungen:{' '}
                        {alert.price_context?.completed_sessions ?? 'nicht belegt'} ·{' '}
                        {alert.price_context?.session_count_basis === 'ORIGINAL_BID'
                          ? 'zur Original-Geldkurszeit'
                          : alert.price_context?.session_count_basis === 'EVALUATION_TIME'
                            ? 'zum Prüfzeitpunkt'
                            : 'Zeitbezug nicht belegt'}{' '}
                        · Stand: {alert.price_context?.session_count_at ?? 'nicht belegt'}
                      </p>
                    )}
                    <p className="mt-1">
                      Ausschließlich ein Hinweis; keine Orderfreigabe und keine automatische Stop-
                      oder Zieländerung.
                    </p>
                    <div className="mt-2 text-xs text-slate-400">
                      <p>
                        Letzter belegter Statuspunkt:{' '}
                        {alert.price_context?.source_status_point ?? 'nicht belegt'}
                      </p>
                      <p>
                        Originalstatuszeit:{' '}
                        {alert.price_context?.source_status_observed_at ?? 'nicht belegt'} ·
                        Erfasst: {alert.price_context?.source_status_captured_at ?? 'nicht belegt'}
                      </p>
                      <p>Fortgeltung nicht belegt.</p>
                    </div>
                    {alert.price_context?.data_problem_reasons && (
                      <details className="mt-2 text-xs text-slate-500">
                        <summary className="cursor-pointer">
                          Gründe des Datenproblems anzeigen
                        </summary>
                        <p className="mt-1 break-all">{alert.price_context.data_problem_reasons}</p>
                      </details>
                    )}
                  </div>
                )}
                {alert.price_context && alert.alert_type !== 'POSITION_REVIEW_DUE' && (
                  <div className="mt-2 text-xs text-slate-400">
                    <p>
                      Quelle: {alert.price_context.provider} ·{' '}
                      {alert.price_context.provider_identity} ·{' '}
                      {alert.price_context.venue_mic ?? 'Handelsplatz nicht angegeben'}
                    </p>
                    <p>
                      Kurszeitpunkt: {alert.price_context.observed_at ?? 'nicht bekannt'} ·
                      Handelstag: {alert.price_context.trading_date ?? '—'} · Abgerufen:{' '}
                      {alert.price_context.retrieved_at ?? '—'}
                    </p>
                    {alert.price_context.quote_time_text && (
                      <p>
                        Zeitangabe der Quelle: {alert.price_context.quote_time_text} ·{' '}
                        {alert.price_context.quote_time_basis === 'DATE_AND_TIMEZONE_UNKNOWN'
                          ? 'Kursdatum und Zeitzone unbekannt'
                          : alert.price_context.quote_time_basis ===
                              'LOCAL_DATETIME_TIMEZONE_UNKNOWN'
                            ? 'Zeitzone unbekannt'
                            : alert.price_context.quote_time_basis}
                      </p>
                    )}
                    {alert.price_context.warning && (
                      <p className="text-amber-300">
                        Indikative Prüfung · {alert.price_context.warning}. Keine Orderfreigabe.
                      </p>
                    )}
                  </div>
                )}
                <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
                  {hasPriceTrigger(alert) && (
                    <>
                      <div>
                        <dt className="text-slate-500">
                          {alert.alert_type === 'HEBELTRADER_B04_LOSS'
                            ? 'Original-Geldkurs'
                            : alert.alert_type === 'INDICATIVE_ENTRY_LOSS'
                              ? 'Beobachteter Geldkurs · indikativ'
                              : 'Beobachtet'}
                        </dt>
                        <dd className="mt-1">
                          {alert.observed_value !== null &&
                          alert.price_context?.basis === 'UNDERLYING_RISK_SIGNAL'
                            ? riskPercent(alert.observed_value)
                            : formatNumber(alert.observed_value)}
                        </dd>
                      </div>
                      <div>
                        <dt className="text-slate-500">
                          {alert.alert_type === 'HEBELTRADER_B04_LOSS' ||
                          alert.alert_type === 'INDICATIVE_ENTRY_LOSS'
                            ? 'Persönlicher Bruttoeinstand je Stück'
                            : 'Schwelle'}
                        </dt>
                        <dd className="mt-1">
                          {alert.threshold_value !== null &&
                          alert.price_context?.basis === 'UNDERLYING_RISK_SIGNAL'
                            ? riskPercent(alert.threshold_value)
                            : formatNumber(alert.threshold_value)}
                        </dd>
                      </div>
                      <div>
                        <dt className="text-slate-500">Marktdaten</dt>
                        <dd className="mt-1">{formatDateTime(alert.market_data_observed_at)}</dd>
                      </div>
                    </>
                  )}
                  <div>
                    <dt className="text-slate-500">Erkannt</dt>
                    <dd className="mt-1">{formatDateTime(alert.detected_at)}</dd>
                  </div>
                </dl>

                <div className="mt-4 border-t border-slate-800 pt-3">
                  <p className="text-xs uppercase tracking-wide text-slate-500">Benachrichtigung</p>
                  {alert.notifications.length === 0 ? (
                    <p className="mt-2 text-sm text-slate-400">Keine Notification erzeugt.</p>
                  ) : (
                    <ul className="mt-2 space-y-2 text-sm">
                      {alert.notifications.map((notification) => (
                        <li key={notification.id}>
                          <span>
                            {alert.status === 'INVALIDATED' && notification.status === 'PENDING'
                              ? 'Versand unterdrückt: Meldung ungültig'
                              : notificationLabel(notification)}
                          </span>
                          {notification.last_delivery?.error_code && (
                            <span className="ml-2 text-slate-500">
                              ({notification.last_delivery.error_code})
                            </span>
                          )}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </li>
            ))}
          </ol>
        )}
      </section>
    </>
  );
}
