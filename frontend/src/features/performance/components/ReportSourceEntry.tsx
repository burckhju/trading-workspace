import { ExecutionCurrencySources } from '../../trade/components/ExecutionCurrencySources';
import { executionCurrencyText } from '../../trade/services/executionCurrency';
import { executionTimeText } from '../services/presentation';
import type { RealizedGrossSource } from '../types/api';

export function ReportSourceEntry({
  source,
  timezone,
}: {
  source: RealizedGrossSource;
  timezone: string;
}) {
  const confirmation = source.currency_confirmation;
  return (
    <li
      aria-label={`Buchungsquelle ${source.execution_id}`}
      className="min-w-0 rounded-lg border border-slate-700 p-3"
    >
      <div className="flex flex-wrap justify-between gap-2">
        <p className="font-medium">
          {source.side} · {source.quantity} Stück
        </p>
        <span className="text-xs text-slate-400">
          {source.is_effective ? 'wirksam' : 'historisch ersetzt'}
        </span>
      </div>
      <p className="mt-1 text-sm">Ausgeführt: {executionTimeText(source, timezone)}</p>
      <p className="mt-1 text-sm">
        Gespeicherter Stückpreis: <code>{source.price_per_unit ?? 'unbekannt'}</code>{' '}
        {source.currency_resolution?.currency_code ??
          confirmation?.currency_code ??
          '· Ausführungswährung unbekannt'}
      </p>
      <p className="mt-1 text-xs text-slate-400">
        Erfasst: {source.recorded_at} · durch {source.recorded_by}
      </p>
      <p className="mt-1 break-all text-xs text-slate-400">
        Buchung {source.execution_id} · Produkt {source.product_id}
      </p>
      {source.supersedes_execution_id && (
        <p className="mt-1 break-all text-xs text-amber-300">
          Ersetzt Buchung {source.supersedes_execution_id}
        </p>
      )}
      {source.superseded_by_execution_id && (
        <p className="mt-1 break-all text-xs text-amber-300">
          Ersetzt durch {source.superseded_by_execution_id}; zählt nicht zusätzlich.
        </p>
      )}
      <div className="mt-3 border-t border-slate-800 pt-2 text-sm">
        {confirmation ? (
          <>
            <p>Währung {confirmation.currency_code} ausdrücklich vom Nutzer bestätigt.</p>
            <p className="text-xs text-slate-400">
              Bestätigt: {confirmation.confirmed_at} · durch {confirmation.confirmed_by}
            </p>
            {confirmation.note && <p>Beleg / Erläuterung: {confirmation.note}</p>}
            <p className="break-all text-xs text-slate-400">Bestätigung {confirmation.id}</p>
          </>
        ) : (
          <p>Ausführungswährung: {executionCurrencyText(source.currency_resolution)}</p>
        )}
        <ExecutionCurrencySources resolution={source.currency_resolution} />
        {source.currency_history.length > 0 && (
          <details className="mt-2">
            <summary className="cursor-pointer">
              Währungshistorie ({source.currency_history.length})
            </summary>
            <ol className="mt-2 space-y-2">
              {source.currency_history.map((entry) => (
                <li key={entry.id} className="break-words border-l border-slate-700 pl-3 text-xs">
                  <p>
                    {entry.currency_code} ·{' '}
                    {entry.id === confirmation?.id ? 'aktuell' : 'historisch ersetzt'} ·
                    ausdrücklich bestätigt
                  </p>
                  <p>
                    {entry.confirmed_at} · durch {entry.confirmed_by}
                  </p>
                  {entry.note && <p>{entry.note}</p>}
                  <p className="break-all">Bestätigung {entry.id}</p>
                  {entry.supersedes_confirmation_id && (
                    <p className="break-all">Ersetzt {entry.supersedes_confirmation_id}</p>
                  )}
                </li>
              ))}
            </ol>
          </details>
        )}
      </div>
      {source.time_precision === 'DATE_ONLY' && (
        <details className="mt-2 text-xs text-slate-400">
          <summary className="cursor-pointer">Datumspräzision</summary>
          <p>
            Das gespeicherte Kalenderdatum und seine Zeitzone bleiben erhalten. Es ist keine
            tatsächliche Ausführungsuhrzeit bekannt.
          </p>
          <p>
            Möglicher Zeitbereich: {source.possible_start_at ?? 'unbekannt'} bis ausschließlich{' '}
            {source.possible_end_at ?? 'unbekannt'}.
          </p>
        </details>
      )}
    </li>
  );
}
