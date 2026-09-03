import { useEffect, useState } from 'react';

import { alertApiClient } from '../services/client';
import type { AlertResponse, NotificationResponse } from '../types/api';

function formatDateTime(value: string | null): string {
  return value ? new Date(value).toLocaleString('de-DE') : '—';
}

function formatNumber(value: string): string {
  return new Intl.NumberFormat('de-DE', { maximumFractionDigits: 10 }).format(Number(value));
}

function alertTitle(alert: AlertResponse): string {
  return alert.alert_type === 'STOP_REACHED' ? 'Stop erreicht' : 'Target erreicht';
}

function notificationLabel(notification: NotificationResponse): string {
  if (notification.status === 'DELIVERED') return `${notification.channel}: zugestellt`;
  if (notification.status === 'FAILED') return `${notification.channel}: fehlgeschlagen`;
  if (notification.last_delivery?.status === 'IN_PROGRESS') return `${notification.channel}: Versand läuft`;
  return `${notification.channel}: ausstehend`;
}

export function TradeAlertsPanel({ tradeId }: { tradeId: string }) {
  const [alerts, setAlerts] = useState<AlertResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    alertApiClient
      .forTrade(tradeId, controller.signal)
      .then(setAlerts)
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(reason instanceof Error ? reason.message : 'Alerts konnten nicht geladen werden.');
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [tradeId]);

  const openCount = alerts.filter((alert) => alert.status === 'OPEN').length;

  return (
    <section className="rounded-xl border border-slate-800 p-5" aria-labelledby="trade-alerts-title">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-wide text-slate-500">Monitoring</p>
          <h2 id="trade-alerts-title" className="mt-1 text-lg font-semibold">
            Positions-Alerts
          </h2>
          <p className="mt-1 text-xs text-slate-500">
            Fachliche Alerts und Notification-Delivery werden getrennt dargestellt.
          </p>
        </div>
        <span className="rounded-full border border-slate-700 px-3 py-1 text-xs">
          {openCount} offen
        </span>
      </div>

      {loading && <p className="mt-4 text-sm text-slate-400">Alerts werden geladen…</p>}
      {error && (
        <p role="alert" className="mt-4 rounded-lg border border-slate-700 p-3 text-sm">
          {error}
        </p>
      )}
      {!loading && !error && alerts.length === 0 && (
        <p className="mt-4 text-sm text-slate-400">Für diesen Trade liegen noch keine Alerts vor.</p>
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
