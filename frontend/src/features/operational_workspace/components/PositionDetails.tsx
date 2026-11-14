import { PositionRiskPanel } from '../../alert/components/PositionRiskPanel';
import { Link } from 'react-router-dom';
import type { OperationalPosition } from '../types';
import { dateLabel, money, numberLabel, purchaseDate, timeLabel } from '../services/positionsView';
import { signalLabel, statusLabel } from '../services/statusLabels';
import { positionPnl } from '../services/positionsView';
import { unrealizedPnlReason } from '../../trade/services/valuationQualification';
import { PositionValuationBasisDetails } from '../../trade/components/PositionValuationBasisDetails';
import { PositionPriceHistory } from './PositionPriceHistory';
import { HebeltraderEvidenceCoverage } from './HebeltraderEvidenceCoverage';

const staleValuationNotice =
  'Kursdaten veraltet: Bewertung und darauf basierende Analysen sind indikativ.';

function valuationNotice(
  p: Pick<OperationalPosition, 'valuation_status' | 'analysis_warning'>,
): string | null {
  // A warning must not turn a missing, failed or unknown status into a quote.
  switch (p.valuation_status) {
    case 'STALE':
      return staleValuationNotice;
    case 'MISSING':
      return 'Produktkurs fehlt.';
    case 'UNAVAILABLE':
      return 'Produktkurs nicht verfügbar.';
    case 'ERROR':
      return 'Fehler bei der Produktbewertung; die genaue Ursache ist nicht bekannt.';
    case 'AVAILABLE':
    case 'LAST_AVAILABLE':
    case 'INDICATIVE':
      break;
    default:
      return 'Bewertungsstatus derzeit nicht einordenbar; die genaue Ursache ist nicht bekannt.';
  }

  switch (p.analysis_warning) {
    case 'OUTDATED_QUOTE_INDICATIVE_ANALYSIS_ONLY':
      // The owner also emits this warning for a regular last-session quote.
      return p.valuation_status === 'LAST_AVAILABLE'
        ? 'Letzter verfügbarer Kursstand; die Analyse ist indikativ.'
        : 'Hinweis zur Kursaktualität: Die Analyse ist indikativ.';
    case 'QUOTE_TIMESTAMP_UNKNOWN_INDICATIVE_ANALYSIS_ONLY':
      return 'Kurszeitpunkt unbekannt: Ein vollständiger, bestätigter Kurszeitpunkt fehlt. Die Analyse ist indikativ.';
    case 'QUOTE_TIMEZONE_UNKNOWN_INDICATIVE_ANALYSIS_ONLY':
      return 'Zeitzone des Kurszeitpunkts unbekannt; die Aktualität ist nicht bestätigt. Die Analyse ist indikativ.';
    case 'QUOTE_REFRESH_FAILED_INDICATIVE_ANALYSIS_ONLY':
      return 'Kursabruf fehlgeschlagen; die Analyse ist indikativ.';
    case 'REFERENCE_PRICE_INDICATIVE_ANALYSIS_ONLY':
      return 'Handels- oder Schlusskurs: Die Analyse ist indikativ.';
    default:
      if (p.analysis_warning) return 'Bewertungshinweis: Die gemeldete Ursache ist nicht bekannt.';
  }

  if (p.valuation_status === 'LAST_AVAILABLE') {
    return 'Letzter verfügbarer Kursstand; die Aktualität ist damit nicht bestätigt.';
  }
  return p.valuation_status === 'INDICATIVE'
    ? 'Indikative Bewertung; Aktualität und Handelbarkeit sind nicht bestätigt.'
    : null;
}

export function PositionDetails({ position: p }: { position: OperationalPosition }) {
  const notice = valuationNotice(p);
  return (
    <section
      aria-label={`Details ${p.product_name}`}
      className="min-w-0 space-y-3 break-words p-4 text-sm"
    >
      <h3 className="font-semibold text-white">{p.product_name} · Positionsdetails</h3>
      <p className="text-slate-300">
        WKN {p.product_wkn ?? 'nicht hinterlegt'} · ISIN {p.product_isin ?? 'nicht hinterlegt'}
      </p>
      <PositionPriceHistory tradeId={p.trade_id} positionId={p.position_id} />
      <HebeltraderEvidenceCoverage
        tradeId={p.trade_id}
        positionId={p.position_id}
        reloadToken={
          p.position_basis?.basis_id ??
          `${p.open_quantity}:${p.cost_basis}:${p.average_entry_price}`
        }
      />
      <dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div>
          <dt className="text-slate-400">Basiswert</dt>
          <dd>{p.underlying_name ?? p.underlying_symbol ?? 'Nicht verfügbar'}</dd>
          {p.underlying_id && (
            <dd>
              <Link
                className="text-sky-300 underline"
                to={`/market-charts?underlying=${p.underlying_id}`}
              >
                Basiswertdiagramm
              </Link>
            </dd>
          )}
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
        <div>
          <dt className="text-slate-400">Nicht realisierter Brutto-G/V</dt>
          <dd>{money(positionPnl(p), p.valuation_currency, true)}</dd>
        </div>
      </dl>
      {positionPnl(p) === null && (
        <p className="text-amber-200">{unrealizedPnlReason(p.unrealized_pnl_reason)}</p>
      )}
      <PositionValuationBasisDetails basis={p.position_basis} />
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
      {notice && <p className="text-amber-200">{notice} Keine Orderfreigabe.</p>}
      <p className="text-xs text-slate-400">
        Stop und Ziel werden unverändert angezeigt. Kein Vergleich zwischen Basiswert-Stop und
        Optionsscheinpreis. Nachkäufe, Teilverkäufe und deren tatsächliche Daten stehen in der
        Trade-Historie.
      </p>
      <PositionRiskPanel tradeId={p.trade_id} readOnly />
      <Link
        to={`${p.target}#execution-dates`}
        className="inline-block rounded border border-slate-600 px-3 py-2 text-sky-200 focus-visible:outline-2 focus-visible:outline-sky-300"
      >
        Kauf-/Verkaufsdaten und Historie öffnen
      </Link>
    </section>
  );
}
