import type { PriceBinding } from '../types/api';

export function PriceBindingInput({
  label,
  value,
  warrantId,
  underlyingId,
  onChange,
}: {
  label: string;
  value: PriceBinding | null;
  warrantId: string;
  underlyingId: string;
  onChange: (value: PriceBinding | null) => void;
}) {
  return (
    <fieldset className="space-y-2 rounded border border-slate-700 p-3">
      <legend>{label}: Kursbezug</legend>
      {!value && (
        <p className="text-sm text-amber-300">
          Kursbezug ungeklärt. Diese Regel wird erst nach ausdrücklicher Zuordnung geprüft.
        </p>
      )}
      <label className="block text-sm">
        Instrument für {label}
        <select
          required
          value={value?.basis ?? ''}
          onChange={(event) => {
            const basis = event.target.value as PriceBinding['basis'];
            onChange(
              basis
                ? {
                    basis,
                    instrument_id: basis === 'WARRANT' ? warrantId : underlyingId,
                    currency: value?.currency ?? '',
                  }
                : null,
            );
          }}
          className="mt-1 w-full rounded border border-slate-700 bg-slate-950 p-2"
        >
          <option value="">Bitte auswählen</option>
          <option value="WARRANT">Optionsschein</option>
          <option value="UNDERLYING">Basiswert</option>
        </select>
      </label>
      <label className="block text-sm">
        Währung für {label}
        <input
          required
          pattern="[A-Z]{3}"
          maxLength={3}
          placeholder="z. B. EUR"
          value={value?.currency ?? ''}
          disabled={!value}
          onChange={(event) =>
            value && onChange({ ...value, currency: event.target.value.toUpperCase() })
          }
          className="mt-1 w-full rounded border border-slate-700 bg-slate-950 p-2"
        />
      </label>
      <p className="text-xs text-slate-400">
        Die Schwelle wird nur mit einem Kurs desselben Instruments in derselben Währung verglichen.
        Indikative Kurse werden gekennzeichnet.
      </p>
    </fieldset>
  );
}
