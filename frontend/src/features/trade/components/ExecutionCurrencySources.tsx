import type { ExecutionCurrencyResolution } from '../types/api';
import { executionCurrencyReason } from '../services/executionCurrency';

export function ExecutionCurrencySources({
  resolution,
}: {
  resolution?: ExecutionCurrencyResolution | null;
}) {
  if (!resolution) return null;
  const reason = executionCurrencyReason(resolution.reason);
  const evidence = resolution.evidence ?? [];
  const automatic =
    resolution.source === 'EXECUTION_DOCUMENT' ||
    resolution.source === 'HISTORICAL_LISTING' ||
    resolution.source === 'HISTORICAL_LISTINGS';
  return (
    <div className="space-y-2 text-sm">
      {automatic && (
        <p>
          Die Währung wurde automatisch aus einer geprüften historischen Quelle abgeleitet. Eine
          erneute Eingabe ist nicht nötig. Bei einer Quellenkorrektur wird die Zuordnung neu
          geprüft.
        </p>
      )}
      {resolution.source === 'PRIOR_BUYS' && (
        <p>
          Die Währung stammt aus den belegten vorherigen Käufen. Eine erneute Eingabe ist nicht
          nötig.
        </p>
      )}
      {resolution.source === 'REPLACED_EXECUTION' && (
        <p>Die belegte Währung der ursprünglichen Buchung wurde für die Korrektur übernommen.</p>
      )}
      {resolution.source === 'UNKNOWN' && (
        <p className="text-amber-300">Die Ausführungswährung ist noch nicht vollständig belegt.</p>
      )}
      {resolution.source === 'MIXED' && (
        <p className="text-amber-300">
          Die Kaufquellen enthalten unterschiedliche Währungen. Es wird keine gemeinsame Währung
          angenommen.
        </p>
      )}
      {resolution.source === 'CONFLICT' && !reason && (
        <p className="text-amber-300">
          Widersprüchliche Währungsbelege verhindern die Berechnung. Bitte die betroffenen Quellen
          prüfen.
        </p>
      )}
      {reason && <p className="text-amber-300">{reason}</p>}
      {(resolution.source_execution_ids.length > 0 ||
        resolution.confirmation_ids.length > 0 ||
        evidence.length > 0 ||
        Boolean(resolution.evidence_ids?.length) ||
        resolution.resolver_version) && (
        <details className="text-xs text-slate-400">
          <summary className="cursor-pointer">Verwendete Währungsherkunft</summary>
          <ul className="mt-2 space-y-1 break-all">
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
                    : 'Historische Handelsnotierungen'}
                  {' · '}erfasst {entry.recorded_at}
                </p>
                {entry.valid_from && entry.valid_to && (
                  <p>
                    Gültig von {entry.valid_from} bis ausschließlich {entry.valid_to}
                  </p>
                )}
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
                <li key={`source-${id}`}>Quellenversion {id}</li>
              ))}
          </ul>
          {resolution.resolver_version && (
            <p className="mt-2">Zuordnungsregel {resolution.resolver_version}</p>
          )}
        </details>
      )}
    </div>
  );
}
