import type { ExecutionCurrencyResolution, PositionValuationBasis } from '../types/api';

const sourceLabels: Record<ExecutionCurrencyResolution['source'], string> = {
  USER_CONFIRMED: 'Direkt bestätigt',
  PRIOR_BUYS: 'Aus vorherigen wirksamen Käufen belegt',
  REPLACED_EXECUTION: 'Aus der korrigierten Ausführung belegt',
  UNKNOWN: 'Nicht belegt',
  MIXED: 'Unterschiedliche Kaufwährungen',
};

export function PositionValuationBasisDetails({
  basis,
}: {
  basis: PositionValuationBasis | null | undefined;
}) {
  if (!basis) return null;
  return (
    <details className="mt-3 min-w-0 rounded border border-slate-700 p-3 text-xs text-slate-400">
      <summary className="cursor-pointer text-slate-300">Kostenbasis und Währungsnachweise</summary>
      <div className="mt-2 space-y-2 break-all">
        <p>
          Kostenbasiswährung:{' '}
          {basis.currency_status === 'KNOWN'
            ? basis.cost_basis_currency
            : basis.currency_status === 'MIXED'
              ? 'Unterschiedliche Kaufwährungen'
              : 'Nicht vollständig belegt'}
        </p>
        <p>
          Bewertungsdefinition: {basis.definition_version} · Lesebasis: {basis.basis_id}
        </p>
        <p>Wirksame Ausführungen: {basis.effective_execution_ids.join(', ') || 'Keine'}</p>
        <ul className="space-y-2">
          {basis.buy_currency_evidence.map((evidence) => (
            <li key={evidence.execution_id}>
              Kauf {evidence.execution_id}: {evidence.currency_code ?? 'Währung nicht belegt'} ·{' '}
              {sourceLabels[evidence.source]}
              <br />
              Quellausführungen: {evidence.source_execution_ids.join(', ') || 'Keine'}
              <br />
              Bestätigungen: {evidence.confirmation_ids.join(', ') || 'Keine'}
            </li>
          ))}
        </ul>
      </div>
    </details>
  );
}
