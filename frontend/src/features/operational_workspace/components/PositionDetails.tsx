import { Link } from 'react-router-dom';
import type { OperationalPosition } from '../types';
import { dateLabel, money, numberLabel, purchaseDate, timeLabel } from '../services/positionsView';
import { signalLabel, statusLabel } from '../services/statusLabels';

export function PositionDetails({ position: p }: { position: OperationalPosition }) {
  return (
    <section aria-label={`Details ${p.product_name}`} className="space-y-3 p-4 text-sm">
      <h3 className="font-semibold text-white">{p.product_name} · Positionsdetails</h3>
      <p className="text-slate-300">
        WKN {p.product_wkn ?? 'nicht hinterlegt'} · ISIN {p.product_isin ?? 'nicht hinterlegt'}
      </p>
      <dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div>
          <dt className="text-slate-400">Basiswert</dt>
          <dd>{p.underlying_name ?? p.underlying_symbol ?? 'Nicht verfügbar'}</dd>
        </div>
        <div>
          <dt className="text-slate-400">Kaufdatum / erster Kauf</dt>
          <dd>{dateLabel(purchaseDate(p))}</dd>
        </div>
        <div>
          <dt className="text-slate-400">Ø Einstand je Stück</dt>
          <dd>{numberLabel(p.average_entry_price)} · Erfasster Kaufpreis, keine FX-Umrechnung</dd>
        </div>
        <div>
          <dt className="text-slate-400">Realisierter Brutto-G/V</dt>
          <dd>{numberLabel(p.realized_gross_pnl)} · Buchungswert</dd>
        </div>
        <div>
          <dt className="text-slate-400">Stop</dt>
          <dd>{numberLabel(p.stop_price)}</dd>
        </div>
        <div>
          <dt className="text-slate-400">Ziel</dt>
          <dd>{numberLabel(p.target_price)}</dd>
        </div>
        <div>
          <dt className="text-slate-400">Monitoring</dt>
          <dd>Monitoring: {statusLabel(p.monitoring_status)}</dd>
        </div>
        <div>
          <dt className="text-slate-400">Marktwert</dt>
          <dd>{money(p.market_value, p.valuation_currency)}</dd>
        </div>
      </dl>
      <p>{signalLabel(p)}</p>
      <p>
        {p.open_alert_count} offene Hinweise
        {p.open_alert_types.length > 0
          ? ` · ${p.open_alert_types.map((t) => (t === 'STOP_REACHED' ? 'Stop erreicht' : t === 'TARGET_REACHED' ? 'Ziel erreicht' : t)).join(', ')}`
          : ''}
      </p>
      <p>
        Quelle: {p.quote_source ?? 'Unbekannt'} · Kurszeitpunkt: {timeLabel(p.quote_observed_at)}
      </p>
      {(p.valuation_status !== 'AVAILABLE' || p.analysis_warning) && (
        <p className="text-amber-200">
          {['LAST_AVAILABLE', 'STALE'].includes(p.valuation_status)
            ? 'Kursdaten veraltet: Bewertung und darauf basierende Analysen sind indikativ.'
            : 'Indikative Bewertung mit dem verfügbaren Referenzkurs; Aktualität und Handelbarkeit sind nicht bestätigt.'}{' '}
          Keine Orderfreigabe.
        </p>
      )}
      <p className="text-xs text-slate-400">
        Stop und Ziel werden unverändert angezeigt. Kein Vergleich zwischen Basiswert-Stop und
        Optionsscheinpreis. Nachkäufe, Teilverkäufe und deren tatsächliche Daten stehen in der
        Trade-Historie.
      </p>
      <Link
        to={`${p.target}#execution-dates`}
        className="inline-block rounded border border-slate-600 px-3 py-2 text-sky-200 focus-visible:outline-2 focus-visible:outline-sky-300"
      >
        Kauf-/Verkaufsdaten und Historie öffnen
      </Link>
    </section>
  );
}
