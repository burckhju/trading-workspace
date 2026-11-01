import { useState, type ReactNode } from 'react';

import { emptyExecutionCurrency, type ExecutionCurrencyDraft } from '../services/executionCurrency';
import { ExecutionCurrencyInput } from './ExecutionCurrencyInput';

export function ExecutionCurrencyOverride({
  value,
  onChange,
  disabled = false,
  correction = false,
  guidance,
  showInput = false,
}: {
  value: ExecutionCurrencyDraft;
  onChange: (value: ExecutionCurrencyDraft) => void;
  disabled?: boolean;
  correction?: boolean;
  guidance?: ReactNode;
  showInput?: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  const inputVisible = expanded || showInput || Boolean(value.code || value.note);
  return (
    <div className="space-y-2 text-sm">
      {guidance ?? (
        <p className="text-slate-400">
          {correction
            ? 'Die belegte Währung der ursprünglichen Buchung bleibt bei dieser Korrektur erhalten.'
            : 'Die Währung wird aus den vorherigen Käufen übernommen, sofern sie vollständig und einheitlich belegt ist.'}{' '}
          Sie müssen die Währung nicht erneut eingeben. Fehlende oder widersprüchliche Herkunft
          bleibt in der Buchung sichtbar.
        </p>
      )}
      {!showInput && (
        <button
          type="button"
          disabled={disabled}
          aria-expanded={inputVisible}
          onClick={() => {
            if (inputVisible) onChange(emptyExecutionCurrency());
            setExpanded(!inputVisible);
          }}
          className="rounded border border-slate-700 px-3 py-2 disabled:opacity-50"
        >
          {inputVisible ? 'Abweichende Währung verwerfen' : 'Abweichende Währung angeben'}
        </button>
      )}
      {inputVisible && (
        <ExecutionCurrencyInput value={value} onChange={onChange} disabled={disabled} />
      )}
    </div>
  );
}
