import { useId } from 'react';

import type { ExecutionCurrencyDraft } from '../services/executionCurrency';

export function ExecutionCurrencyInput({
  value,
  onChange,
  disabled = false,
}: {
  value: ExecutionCurrencyDraft;
  onChange: (value: ExecutionCurrencyDraft) => void;
  disabled?: boolean;
}) {
  const id = useId();
  return (
    <fieldset disabled={disabled} className="mt-4 space-y-3 rounded-lg border border-slate-700 p-3">
      <legend className="px-1 text-sm font-medium">Tatsächliche Ausführungswährung</legend>
      <p id={`${id}-help`} className="text-sm text-slate-400">
        Geben Sie die Währung des tatsächlichen Stückpreises an, zum Beispiel laut Abrechnung. Mit
        dem Speichern bestätigen Sie diese Angabe. Eine Produktnotierung oder die Berichtswährung
        wird nicht als Ausführungswährung übernommen.
      </p>
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="block text-sm" htmlFor={`${id}-code`}>
          Ausführungswährung (Code)
          <input
            id={`${id}-code`}
            value={value.code}
            onChange={(event) => onChange({ ...value, code: event.target.value.toUpperCase() })}
            maxLength={3}
            autoCapitalize="characters"
            autoComplete="off"
            spellCheck={false}
            aria-describedby={`${id}-help`}
            placeholder="z. B. EUR"
            className="mt-1 block w-full rounded border border-slate-700 bg-slate-950 p-2"
          />
        </label>
        <label className="block text-sm" htmlFor={`${id}-note`}>
          Beleg / Erläuterung (optional)
          <input
            id={`${id}-note`}
            value={value.note}
            maxLength={1000}
            onChange={(event) => onChange({ ...value, note: event.target.value })}
            className="mt-1 block w-full rounded border border-slate-700 bg-slate-950 p-2"
          />
        </label>
      </div>
    </fieldset>
  );
}
