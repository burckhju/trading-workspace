import { useId } from 'react';

import type { ExecutionCurrencyDraft } from '../services/executionCurrency';

export function ExecutionCurrencyInput({
  value,
  onChange,
  disabled = false,
  replacement = false,
}: {
  value: ExecutionCurrencyDraft;
  onChange: (value: ExecutionCurrencyDraft) => void;
  disabled?: boolean;
  replacement?: boolean;
}) {
  const id = useId();
  return (
    <fieldset disabled={disabled} className="mt-4 space-y-3 rounded-lg border border-slate-700 p-3">
      <legend className="px-1 text-sm font-medium">Tatsächliche Ausführungswährung</legend>
      <p id={`${id}-help`} className="text-sm text-slate-400">
        {replacement
          ? 'Die Ersatzbuchung braucht eine eigene Währungsbestätigung. Eine frühere Bestätigung wird nicht übernommen.'
          : 'Maßgeblich ist die Währung des tatsächlichen Stückpreises, zum Beispiel laut Abrechnung.'}{' '}
        Ohne ausdrückliche Bestätigung bleibt die Währung unbekannt. Eine Produktnotierung oder die
        Berichtswährung ist kein Beleg.
      </p>
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="block text-sm" htmlFor={`${id}-code`}>
          Ausführungswährung (Code)
          <input
            id={`${id}-code`}
            value={value.code}
            onChange={(event) =>
              onChange({ ...value, code: event.target.value.toUpperCase(), confirmed: false })
            }
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
            onChange={(event) => onChange({ ...value, note: event.target.value, confirmed: false })}
            className="mt-1 block w-full rounded border border-slate-700 bg-slate-950 p-2"
          />
        </label>
      </div>
      <label className="flex items-start gap-2 text-sm">
        <input
          type="checkbox"
          checked={value.confirmed}
          disabled={disabled || !/^[A-Z]{3}$/.test(value.code.trim())}
          onChange={(event) => onChange({ ...value, confirmed: event.target.checked })}
          className="mt-1"
        />
        Ich bestätige {value.code.trim() || 'die angegebene Währung'} als tatsächliche Währung
        dieser Ausführung.
      </label>
    </fieldset>
  );
}
