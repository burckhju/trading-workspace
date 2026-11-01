import { currencyResolutionLabel } from '../services/realizedCurrencyNotice';
import type { RealizedGrossSource } from '../types/api';

/** Already-read provenance for the Realized pilot; no qualification or commands. */
export function ReportCurrencyEvidence({ source }: { source: RealizedGrossSource }) {
  const resolution = source.currency_resolution;
  const confirmation = source.currency_confirmation;
  const evidence = resolution?.evidence ?? [];
  return (
    <div className="min-w-0 space-y-2 text-sm">
      <p>
        Ausführungswährung:{' '}
        {resolution
          ? currencyResolutionLabel(resolution)
          : 'In dieser Antwort ist keine Währungsauflösung enthalten.'}
      </p>
      <details className="min-w-0 text-xs text-slate-400">
        <summary className="cursor-pointer rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400">
          Verwendete Währungsherkunft
        </summary>
        <div className="mt-2 min-w-0 space-y-3 break-words [overflow-wrap:anywhere]">
          <p>Buchung {source.execution_id}</p>
          {confirmation && (
            <div className="space-y-1">
              <p>Währung {confirmation.currency_code} ausdrücklich vom Nutzer bestätigt.</p>
              <p>
                Bestätigt: {confirmation.confirmed_at} · durch {confirmation.confirmed_by}
              </p>
              {confirmation.note && <p>Beleg / Erläuterung: {confirmation.note}</p>}
              <p>Bestätigung {confirmation.id}</p>
              {confirmation.supersedes_confirmation_id && (
                <p>Ersetzt Bestätigung {confirmation.supersedes_confirmation_id}</p>
              )}
            </div>
          )}
          {resolution && (
            <>
              <p>Gemeldete Herkunft: {resolution.source}</p>
              {resolution.reason && <p>Originalgrund: {resolution.reason}</p>}
              {resolution.resolver_version && <p>Zuordnungsregel {resolution.resolver_version}</p>}
              <ul className="space-y-1">
                {resolution.source_execution_ids.map((id) => (
                  <li key={`execution-${id}`}>Buchung {id}</li>
                ))}
                {resolution.confirmation_ids.map((id) => (
                  <li key={`confirmation-${id}`}>Bestätigung {id}</li>
                ))}
                {evidence.map((entry) => (
                  <li
                    key={`evidence-${entry.id}`}
                    className="space-y-1 rounded border border-slate-800 p-2"
                  >
                    <p>Quelle: {entry.source_reference}</p>
                    <p>
                      {entry.kind === 'EXECUTION_DOCUMENT'
                        ? 'Zugeordneter Ausführungsbeleg'
                        : entry.kind === 'HISTORICAL_LISTING' ||
                            entry.kind === 'HISTORICAL_LISTINGS'
                          ? 'Historische Handelsnotierungen'
                          : 'Gemeldeter Währungsbeleg'}
                      {' · '}erfasst {entry.recorded_at}
                    </p>
                    {entry.valid_from && <p>Gültig ab {entry.valid_from}</p>}
                    {entry.valid_to && <p>Gültig bis ausschließlich {entry.valid_to}</p>}
                    <p>Quellenversion {entry.id}</p>
                    {entry.source_fingerprint && <p>Quellennachweis {entry.source_fingerprint}</p>}
                    {entry.verification === 'USER_VERIFIED_SOURCE' && (
                      <p>Originalquelle vom Nutzer geprüft</p>
                    )}
                    {entry.supersedes_evidence_id && (
                      <p>Ersetzt Quelle {entry.supersedes_evidence_id}</p>
                    )}
                  </li>
                ))}
                {(resolution.evidence_ids ?? [])
                  .filter((id) => !evidence.some((entry) => entry.id === id))
                  .map((id) => (
                    <li key={`evidence-reference-${id}`}>Quellenversion {id}</li>
                  ))}
              </ul>
            </>
          )}
        </div>
      </details>
      {source.currency_history.length > 0 && (
        <details className="min-w-0 text-xs text-slate-400">
          <summary className="cursor-pointer rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400">
            Währungshistorie ({source.currency_history.length})
          </summary>
          <ol className="mt-2 space-y-2 break-words [overflow-wrap:anywhere]">
            {source.currency_history.map((entry) => (
              <li key={entry.id} className="space-y-1 border-l border-slate-700 pl-3">
                <p>
                  {entry.currency_code} ·{' '}
                  {entry.id === confirmation?.id ? 'aktuell' : 'historisch ersetzt'} · ausdrücklich
                  bestätigt
                </p>
                <p>
                  {entry.confirmed_at} · durch {entry.confirmed_by}
                </p>
                {entry.note && <p>{entry.note}</p>}
                <p>Bestätigung {entry.id}</p>
                {entry.supersedes_confirmation_id && (
                  <p>Ersetzt {entry.supersedes_confirmation_id}</p>
                )}
              </li>
            ))}
          </ol>
        </details>
      )}
    </div>
  );
}
