import { useState } from 'react';

import { emptyExecutionCurrency, type ExecutionCurrencyDraft } from '../services/executionCurrency';
import { ExecutionCurrencyInput } from './ExecutionCurrencyInput';

export function ExecutionCurrencyOverride({
  value,
  onChange,
  disabled = false,
  correction = false,
}: {
  value: ExecutionCurrencyDraft;
  onChange: (value: ExecutionCurrencyDraft) => void;
  disabled?: boolean;
  correction?: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="space-y-2 text-sm">
      <p className="text-slate-400">
        {correction
          ? 'Die belegte Währung der ursprünglichen Buchung bleibt bei dieser Korrektur erhalten.'
          : 'Die Währung wird aus den vorherigen Käufen übernommen, sofern sie vollständig und einheitlich belegt ist.'}{' '}
        Sie müssen die Währung nicht erneut eingeben. Fehlende oder widersprüchliche Herkunft bleibt
        in der Buchung sichtbar.
      </p>
      <button
        type="button"
        disabled={disabled}
        aria-expanded={expanded}
        onClick={() => {
          if (expanded) onChange(emptyExecutionCurrency());
          setExpanded(!expanded);
        }}
        className="rounded border border-slate-700 px-3 py-2 disabled:opacity-50"
      >
        {expanded ? 'Abweichende Währung verwerfen' : 'Abweichende Währung angeben'}
      </button>
      {expanded && <ExecutionCurrencyInput value={value} onChange={onChange} disabled={disabled} />}
    </div>
  );
}
