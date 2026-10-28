import { executionCurrencyText } from '../services/executionCurrency';
import type { PositionValuationBasis } from '../types/api';
import { ExecutionCurrencySources } from './ExecutionCurrencySources';

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
            <li key={evidence.execution_id} className="space-y-2">
              <p>
                Kauf {evidence.execution_id}: {executionCurrencyText(evidence)}
              </p>
              <ExecutionCurrencySources resolution={evidence} />
            </li>
          ))}
        </ul>
      </div>
    </details>
  );
}
