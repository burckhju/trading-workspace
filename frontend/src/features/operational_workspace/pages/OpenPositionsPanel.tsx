import { Link } from 'react-router-dom';

import type { OperationalPosition } from '../types';

function formatNumber(value: string | null, currency?: string | null): string {
  if (value === null) return '—';
  const formatted = new Intl.NumberFormat('de-DE', { maximumFractionDigits: 2 }).format(
    Number(value),
  );
  return currency ? `${formatted} ${currency}` : formatted;
}

function statusLabel(status: string): string {
  if (status === 'OK' || status === 'AVAILABLE') return 'Aktuell';
  if (status === 'LAST_AVAILABLE') return 'Letzter verfügbarer Kurs';
  if (status === 'STALE') return 'Veraltet';
  if (status === 'MISSING') return 'Fehlt';
  if (status === 'INSUFFICIENT') return 'Noch nicht ausreichend';
  if (status === 'UNAVAILABLE') return 'Nicht verfügbar';
  return 'Prüfen';
}

function attentionLabel(position: OperationalPosition): string {
  if (position.attention_state === 'ALERT') {
    return position.open_alert_count === 1
      ? '1 offener Hinweis'
      : `${position.open_alert_count} offene Hinweise`;
  }
  if (position.attention_state === 'DATA_HEALTH') return 'Daten prüfen';
  return 'Normal';
}

function positionSignalLabel(position: OperationalPosition): string {
  const signal = position.position_signal;
  if (!signal) return 'Positionssignal: nicht verfügbar';
  if (signal.quality_status !== 'AVAILABLE') {
    if (signal.quality_status === 'STALE') return 'Positionssignal: Daten veraltet';
    if (signal.quality_status === 'MISSING') return 'Positionssignal: Daten fehlen';
    if (signal.quality_status === 'INSUFFICIENT') {
      return 'Positionssignal: noch nicht ausreichend Daten';
    }
    return 'Positionssignal: Prüfung erforderlich';
  }
  if (signal.alert_level === 'CRITICAL') return 'Positionssignal: dynamischer Stop erreicht';
  if (signal.alert_level === 'ATTENTION') return 'Positionssignal: Gewinnschutz aktiv';
  return 'Positionssignal: keine besondere Aufmerksamkeit nötig';
}

export function OpenPositionsPanel({ positions }: { positions: OperationalPosition[] }) {
  if (positions.length === 0) return null;

  return (
    <section aria-labelledby="open-positions-heading">
      <div className="mb-3">
        <h2 id="open-positions-heading" className="text-xl font-semibold text-white">
          Offene Positionen <span className="text-slate-500">· {positions.length}</span>
        </h2>
        <p className="mt-1 text-sm text-slate-400">
          Kompakter Depotstatus aus bestehenden Positions-, Monitoring-, Bewertungs- und
          Hinweisdaten.
        </p>
      </div>
      <ul className="grid gap-3 xl:grid-cols-2">
        {positions.map((position) => (
          <li
            key={position.position_id}
            className="rounded-xl border border-slate-800 bg-slate-900/60 p-5"
          >
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-500">
                  {position.product_symbol ?? position.product_name}
                </p>
                <h3 className="mt-1 text-lg font-semibold text-white">{position.product_name}</h3>
              </div>
              <span className="rounded-full border border-slate-700 px-2.5 py-1 text-xs text-slate-300">
                {attentionLabel(position)}
              </span>
            </div>

            <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-3 text-sm sm:grid-cols-4">
              <div>
                <dt className="text-slate-500">Stück</dt>
                <dd className="mt-1 text-slate-200">{position.open_quantity}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Ø Einstand</dt>
                <dd className="mt-1 text-slate-200">
                  {formatNumber(position.average_entry_price)}
                </dd>
              </div>
              <div>
                <dt className="text-slate-500">Marktwert</dt>
                <dd className="mt-1 text-slate-200">
                  {formatNumber(position.market_value, position.valuation_currency)}
                </dd>
              </div>
              <div>
                <dt className="text-slate-500">Nicht realisierter G/V</dt>
                <dd className="mt-1 text-slate-200">
                  {formatNumber(position.unrealized_gross_pnl, position.valuation_currency)}
                </dd>
              </div>
              <div>
                <dt className="text-slate-500">Realisierter G/V</dt>
                <dd className="mt-1 text-slate-200">
                  {formatNumber(position.realized_gross_pnl, position.valuation_currency)}
                </dd>
              </div>
              <div>
                <dt className="text-slate-500">Stop</dt>
                <dd className="mt-1 text-slate-200">{formatNumber(position.stop_price)}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Ziel</dt>
                <dd className="mt-1 text-slate-200">{formatNumber(position.target_price)}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Basiswert</dt>
                <dd className="mt-1 text-slate-200">{position.underlying_symbol ?? '—'}</dd>
              </div>
            </dl>

            {position.valuation_status === 'LAST_AVAILABLE' && (
              <p className="mt-3 text-sm text-amber-300">
                Kursdaten veraltet: Bewertung und darauf basierende Analysen sind indikativ.
                Kurszeitpunkt und Quelle unter „Trade verwalten“ prüfen. Keine Orderfreigabe.
              </p>
            )}

            <div className="mt-4 flex flex-wrap gap-2 text-xs text-slate-300">
              <span className="rounded-full border border-slate-700 px-2.5 py-1">
                Monitoring: {statusLabel(position.monitoring_status)}
              </span>
              <span className="rounded-full border border-slate-700 px-2.5 py-1">
                Produktkurs: {statusLabel(position.valuation_status)}
              </span>
              <span className="rounded-full border border-slate-700 px-2.5 py-1">
                {positionSignalLabel(position)}
              </span>
              {position.open_alert_types.map((alertType) => (
                <span key={alertType} className="rounded-full border border-slate-700 px-2.5 py-1">
                  {alertType === 'STOP_REACHED' ? 'Stop erreicht' : 'Ziel erreicht'}
                </span>
              ))}
            </div>

            <div className="mt-4 flex flex-wrap justify-end gap-2">
              <Link
                to={position.target}
                className="rounded-lg border border-slate-600 px-3 py-2 text-sm font-medium text-slate-100 hover:border-slate-400"
              >
                Trade verwalten
              </Link>
              <Link
                to={position.target}
                className="rounded-lg bg-slate-100 px-3 py-2 text-sm font-medium text-slate-950 hover:bg-white"
              >
                Verkauf erfassen
              </Link>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
