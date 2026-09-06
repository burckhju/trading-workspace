import { useEffect, useState } from 'react';

import { alertApiClient } from '../services/client';
import type {
  AlertResponse,
  NotificationResponse,
  PositionMonitoringHealthResponse,
  PositionValuationResponse,
} from '../types/api';

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

function money(value: string | null, currency: string | null): string {
  if (value === null) return '—';
  const number = Number(value);
  if (!currency) return formatNumber(value);
  return new Intl.NumberFormat('de-DE', {
    style: 'currency',
    currency,
    maximumFractionDigits: 10,
  }).format(number);
}

function alertTitle(alert: AlertResponse): string {
  return alert.alert_type === 'STOP_REACHED' ? 'Stop erreicht' : 'Target erreicht';
}

function notificationLabel(notification: NotificationResponse): string {
  if (notification.status === 'DELIVERED') return `${notification.channel}: zugestellt`;
  if (notification.status === 'FAILED') return `${notification.channel}: fehlgeschlagen`;
  if (notification.last_delivery?.status === 'IN_PROGRESS')
    return `${notification.channel}: Versand läuft`;
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
    return 'Die Underlying-Marktdaten sind für die Stop-/Target-Überwachung aktuell genug.';
  }
  if (health.status === 'STALE') {
    return 'Die letzten completed-daily Underlying-Daten sind zu alt. Daraus wird kein Stop-/Target-Alert abgeleitet.';
  }
  if (health.status === 'MISSING') {
    return 'Es liegen keine completed-daily Underlying-Daten vor. Daraus wird kein Stop-/Target-Alert abgeleitet.';
  }
  return 'Die Monitoring-Daten konnten nicht verlässlich ausgewertet werden. Es wird kein scheinbar normaler Stop-/Target-Zustand angenommen.';
}

function valuationLabel(valuation: PositionValuationResponse): string {
  if (valuation.status === 'OK') return 'Indicative Bewertung verfügbar';
  if (valuation.status === 'MISSING') return 'Produktkurs fehlt';
  if (valuation.status === 'UNAVAILABLE') return 'Bewertung nicht verfügbar';
  return 'Bewertungsproblem';
}

function valuationExplanation(valuation: PositionValuationResponse): string {
  if (valuation.status === 'OK') {
    return 'Die offene LONG-Position wird indikativ zum Bid des historisch ausgewählten WarrantListings bewertet. Unrealized P&L ist gross vor Gebühren, Steuern und Transaktionskosten.';
  }
  if (valuation.status === 'UNAVAILABLE') {
    return 'Für diesen Trade ist kein eindeutiges historisches WarrantListing belegt. Die Anwendung rät deshalb keinen Produktkurs.';
  }
  if (valuation.status === 'MISSING') {
    return 'Für das historisch ausgewählte WarrantListing liegt kein verwendbarer Bid vor. Marktwert und unrealized gross P&L werden nicht geschätzt.';
  }
  return 'Die Produktbewertung konnte nicht verlässlich durchgeführt werden. Marktwert und unrealized gross P&L werden nicht geschätzt.';
}

export function TradeAlertsPanel({ tradeId }: { tradeId: string }) {
  const [alerts, setAlerts] = useState<AlertResponse[]>([]);
  const [health, setHealth] = useState<PositionMonitoringHealthResponse | null>(null);
  const [valuation, setValuation] = useState<PositionValuationResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    setHealth(null);
    setValuation(null);

    const alertsRequest = alertApiClient.forTrade(tradeId, controller.signal).then(setAlerts);
    const healthRequest = alertApiClient
      .monitoringHealth(tradeId, controller.signal)
      .then(setHealth)
      .catch(() => {
        if (!controller.signal.aborted) setHealth(null);
      });
    const valuationRequest = alertApiClient
      .valuation(tradeId, controller.signal)
      .then(setValuation)
      .catch(() => {
        if (!controller.signal.aborted) setValuation(null);
      });

    Promise.all([alertsRequest, healthRequest, valuationRequest])
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
    <section
      className="rounded-xl border border-slate-800 p-5"
      aria-labelledby="trade-alerts-title"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-wide text-slate-500">Monitoring</p>
          <h2 id="trade-alerts-title" className="mt-1 text-lg font-semibold">
            Position &amp; Alerts
          </h2>
          <p className="mt-1 text-xs text-slate-500">
            Produktbewertung, Underlying-Datenzustand, fachliche Alerts und Notification-Delivery
            bleiben getrennte Sichten.
          </p>
        </div>
        <span className="rounded-full border border-slate-700 px-3 py-1 text-xs">
          {openCount} Alerts offen
        </span>
      </div>

      {valuation && (
        <div className="mt-4 rounded-lg border border-slate-800 p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-500">Produktbewertung</p>
              <p className="mt-1 font-medium">{valuationLabel(valuation)}</p>
            </div>
            <span className="rounded-full border border-slate-700 px-2.5 py-1 text-xs">
              {valuation.status}
            </span>
          </div>
          <p className="mt-2 text-sm text-slate-400">{valuationExplanation(valuation)}</p>
          <dl className="mt-3 grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
            <div>
              <dt className="text-slate-500">Bid / Ask</dt>
              <dd className="mt-1">
                {formatNumber(valuation.bid)} / {formatNumber(valuation.ask)}{' '}
                {valuation.currency ?? ''}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">Markierung</dt>
              <dd className="mt-1">
                {valuation.mark_price_type ?? '—'} · {money(valuation.mark_price, valuation.currency)}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">Marktwert</dt>
              <dd className="mt-1">{money(valuation.market_value, valuation.currency)}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Unrealized gross P&amp;L</dt>
              <dd className="mt-1">{money(valuation.unrealized_gross_pnl, valuation.currency)}</dd>
            </div>
          </dl>
          <p className="mt-3 text-xs text-slate-500">
            Quote-Zeitpunkt: {formatDateTime(valuation.observed_at)}
          </p>
          {valuation.status !== 'OK' && (
            <details className="mt-3 text-xs text-slate-500">
              <summary className="cursor-pointer">Technischen Grund anzeigen</summary>
              <p className="mt-2 break-all">{valuation.reason}</p>
            </details>
          )}
        </div>
      )}

      {health && (
        <div className="mt-4 rounded-lg border border-slate-800 p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-500">
                Underlying-Marktdatenstatus
              </p>
              <p className="mt-1 font-medium">{healthLabel(health)}</p>
            </div>
            <span className="rounded-full border border-slate-700 px-2.5 py-1 text-xs">
              {health.status}
            </span>
          </div>
          <p className="mt-2 text-sm text-slate-400">{healthExplanation(health)}</p>
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
          {health.status !== 'OK' && (
            <details className="mt-3 text-xs text-slate-500">
              <summary className="cursor-pointer">Technischen Grund anzeigen</summary>
              <p className="mt-2 break-all">{health.reason}</p>
            </details>
          )}
        </div>
      )}

      {loading && <p className="mt-4 text-sm text-slate-400">Monitoring wird geladen…</p>}
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
                  <p className="mt-1 text-sm text-slate-400">{alert.reason}</p>
                </div>
                <span className="rounded-full border border-slate-700 px-2.5 py-1 text-xs">
                  {alert.status === 'OPEN' ? 'OPEN' : 'RESOLVED'}
                </span>
              </div>

              <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
                <div>
                  <dt className="text-slate-500">Beobachtet</dt>
                  <dd className="mt-1">{formatNumber(alert.observed_value)}</dd>
                </div>
                <div>
                  <dt className="text-slate-500">Schwelle</dt>
                  <dd className="mt-1">{formatNumber(alert.threshold_value)}</dd>
                </div>
                <div>
                  <dt className="text-slate-500">Marktdaten</dt>
                  <dd className="mt-1">{formatDateTime(alert.market_data_observed_at)}</dd>
                </div>
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
                        <span>{notificationLabel(notification)}</span>
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
  );
}
