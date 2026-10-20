import type { ExecutionCurrencyResolution } from '../types/api';

export function ExecutionCurrencySources({
  resolution,
}: {
  resolution?: ExecutionCurrencyResolution | null;
}) {
  if (!resolution) return null;
  return (
    <div className="space-y-2 text-sm">
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
      {(resolution.source_execution_ids.length > 0 || resolution.confirmation_ids.length > 0) && (
        <details className="text-xs text-slate-400">
          <summary className="cursor-pointer">Verwendete Währungsherkunft</summary>
          <ul className="mt-2 space-y-1 break-all">
            {resolution.source_execution_ids.map((id) => (
              <li key={`execution-${id}`}>Buchung {id}</li>
            ))}
            {resolution.confirmation_ids.map((id) => (
              <li key={`confirmation-${id}`}>Bestätigung {id}</li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}
